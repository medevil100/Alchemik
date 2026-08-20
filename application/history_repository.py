class HistoryRepository:
    """Właściciel kontraktu trwałości dla cykli, MarketEvent i Observation."""

    def __init__(self):
        self._cycles = {}
        self._observations = {}
        self._readings = {}
        self._universe = {}
        self._snapshots = {}

    # ------------------------------------------------------------------
    # Kontrakt trwałości InstrumentReading / InstrumentObservation
    # ------------------------------------------------------------------

    def _latest_revision(self, instrument_id: str, market_data_timestamp):
        """Najnowsza rewizja dla tożsamości (instrument_id, timestamp) lub None."""
        versions = [
            r for r in self._readings.values()
            if r.instrument_id == instrument_id
            and r.market_data_timestamp == market_data_timestamp
        ]
        if not versions:
            return None
        return max(versions, key=lambda r: r.revision_number)

    def save_reading(self, observation, reading) -> str:
        """
        Atomowo zapisz InstrumentObservation i InstrumentReading z obsługą rewizji.

        Zwraca dokładnie jeden z wyników:
          * ``ACCEPTED``                 — nowy fakt (revision 1, supersedes NULL)
          * ``DUPLICATE_NO_OP``          — identyczny timestamp i treść, bez zmian
          * ``SOURCE_REVISION_ACCEPTED`` — zmieniona treść tego samego timestampu,
                                            instrumentu, Observation i źródła;
                                            nowa rewizja z supersedes_reading_id
          * ``CONFLICT``                 — obca tożsamość, uszkodzone supersedes
                                            albo ta sama tożsamość, inna treść;
                                            Observation → INTEGRITY_BREACHED
          * ``STALE_TIMESTAMP``          — starszy timestamp, odrzucony bez
                                            naruszenia integralności
        """
        instrument_id = observation.instrument_id
        observation_id = observation.observation_id
        market_ts = reading.market_data_timestamp

        # Obca tożsamość instrumentu → CONFLICT (nie jest rewizją)
        if reading.instrument_id != instrument_id:
            return "CONFLICT"

        # Check for existing latest revision with same identity
        existing = self._latest_revision(instrument_id, market_ts)
        if existing is not None:
            same_content = (
                reading.open == existing.open
                and reading.high == existing.high
                and reading.low == existing.low
                and reading.close == existing.close
                and reading.volume == existing.volume
                and reading.data_completeness == existing.data_completeness
                and reading.source == existing.source
            )

            reference = reading.supersedes_reading_id
            valid_ref = (
                reference is None
                or reference == existing.reading_id
            )

            if same_content:
                # Identyczna treść — rewizja niepotrzebna; uszkodzone
                # supersedes przy identycznej treści = CONFLICT.
                return "DUPLICATE_NO_OP" if valid_ref else "CONFLICT"

            # Zmieniona treść tego samego timestampu.
            if (reading.observation_id != existing.observation_id) or (reading.source != existing.source):
                observation.terminate("INTEGRITY_BREACHED", "Content conflict")
                self._observations[instrument_id] = observation
                return "CONFLICT"

            if not valid_ref:
                # Uszkodzone supersedes przy zmienionej treści → CONFLICT.
                return "CONFLICT"

            # Poprawna rewizja źródła: ta sama tożsamość, Observation i źródło.
            # InstrumentReading jest immutable — tworzymy nowy obiekt z polami rewizji.
            from data.models.instrument_reading import InstrumentReading
            new_revision = existing.revision_number + 1
            source_revision = InstrumentReading(
                reading_id=reading.reading_id,
                observation_id=reading.observation_id,
                instrument_id=reading.instrument_id,
                market_data_timestamp=reading.market_data_timestamp,
                scan_timestamp=reading.scan_timestamp,
                open=reading.open,
                high=reading.high,
                low=reading.low,
                close=reading.close,
                volume=reading.volume,
                source=reading.source,
                prev_reading_id=existing.reading_id,
                data_completeness=reading.data_completeness,
                revision_number=new_revision,
                supersedes_reading_id=existing.reading_id,
            )
            self._observations[instrument_id] = observation
            self._readings[(instrument_id, market_ts, new_revision)] = source_revision
            return "SOURCE_REVISION_ACCEPTED"

        # Check for STALE_TIMESTAMP
        for stored_rdg in self._readings.values():
            if stored_rdg.instrument_id == instrument_id:
                if market_ts < stored_rdg.market_data_timestamp:
                    return "STALE_TIMESTAMP"

        # Determine prev_reading_id — najnowsza rewizja najnowszego timestampu
        prev_reading_id = None
        instrument_readings = [
            r for r in self._readings.values()
            if r.instrument_id == instrument_id
        ]
        if instrument_readings:
            latest_rdg = max(
                instrument_readings,
                key=lambda r: (r.market_data_timestamp, r.revision_number),
            )
            prev_reading_id = latest_rdg.reading_id

        # Store observation
        self._observations[instrument_id] = observation

        # Store reading (revision 1, supersedes NULL)
        # InstrumentReading jest immutable — tworzymy nowy obiekt z polami rewizji.
        from data.models.instrument_reading import InstrumentReading
        accepted_reading = InstrumentReading(
            reading_id=reading.reading_id,
            observation_id=reading.observation_id,
            instrument_id=reading.instrument_id,
            market_data_timestamp=reading.market_data_timestamp,
            scan_timestamp=reading.scan_timestamp,
            open=reading.open,
            high=reading.high,
            low=reading.low,
            close=reading.close,
            volume=reading.volume,
            source=reading.source,
            prev_reading_id=prev_reading_id,
            data_completeness=reading.data_completeness,
            revision_number=1,
            supersedes_reading_id=None,
        )
        self._readings[(instrument_id, market_ts, 1)] = accepted_reading
        return "ACCEPTED"

    # ------------------------------------------------------------------
    # Kontrakt trwałego rejestru uniwersum (Krok 3/8)
    # ------------------------------------------------------------------

    def save_universe_snapshot(self, snapshot) -> None:
        """Atomowy zapis snapshotu uniwersum (pamięciowy odpowiednik)."""
        from data.models.universe_instrument import UniverseInstrument
        now = snapshot.created_at
        seen = set()
        for inst in snapshot.instruments:
            row = inst.to_row()
            if row["symbol"] in seen:
                continue
            seen.add(row["symbol"])
            if row["symbol"] in self._universe:
                existing = self._universe[row["symbol"]]
                existing.last_seen_at = row["last_seen_at"] or existing.last_seen_at
                existing.status = "ACTIVE" if row["status"] == "ACTIVE" else row["status"]
                existing.chart_status = row["chart_status"]
                existing.candles_received = row["candles_received"]
                existing.candles_valid = row["candles_valid"]
                existing.candles_rejected = row["candles_rejected"]
                existing.rejection_reasons = dict(row["rejection_reasons"] or {})
                existing.baseline_status = row["baseline_status"] or existing.baseline_status
                if row["last_reading_id"]:
                    existing.last_reading_id = row["last_reading_id"]
            else:
                self._universe[row["symbol"]] = UniverseInstrument(**row)
        # Oznacz wcześniej znane, nieobecne jako MISSING_IN_CURRENT_SCAN.
        present = set(seen)
        for sym, inst in self._universe.items():
            if sym not in present:
                inst.status = "MISSING_IN_CURRENT_SCAN"
        self._snapshots[snapshot.snapshot_id] = snapshot

    def get_current_universe(self) -> list:
        """Zwróć aktualne uniwersum (bez usuwania instrumentów)."""
        return list(self._universe.values())

    def get_snapshot(self, snapshot_id: str):
        """Zwróć konkretny snapshot lub None."""
        return self._snapshots.get(snapshot_id)

    def get_latest_snapshot(self):
        """Zwróć ostatni snapshot (wg kolejności zapisu) lub None."""
        if not self._snapshots:
            return None
        return self._snapshots[max(self._snapshots.keys())]

    def restore_universe(self) -> list:
        """Jawne odtworzenie uniwersum po restarcie (pamięciowe)."""
        return self.get_current_universe()

    def load_observation(self, instrument_id: str):
        """
        Wczytaj ACTIVE InstrumentObservation po instrument_id.

        Zwraca ``InstrumentObservation`` lub ``None``, jeżeli instrument
        nie ma ACTIVE Observation.
        """
        obs = self._observations.get(instrument_id)
        if obs is not None and obs.state == "ACTIVE":
            return obs
        return None

    def restore_active_observations(self) -> list:
        """
        Przywróć wszystkie ACTIVE Observations wraz z ich ostatnim
        zaakceptowanym Readingiem (wg największego market_data_timestamp,
        a dla tego samego timestampu — najwyższego revision_number).

        Zwraca listę krotek ``(InstrumentObservation, InstrumentReading)``.
        """
        results = []
        for instrument_id, obs in self._observations.items():
            if obs.state != "ACTIVE":
                continue
            instrument_readings = [
                r for r in self._readings.values()
                if r.instrument_id == instrument_id
            ]
            if not instrument_readings:
                continue
            latest = max(
                instrument_readings,
                key=lambda r: (r.market_data_timestamp, r.revision_number),
            )
            results.append((obs, latest))
        return results

    # ------------------------------------------------------------------
    # Istniejący kontrakt cykli
    # ------------------------------------------------------------------

    def save_cycle(self, cycle_id, cycle_data):
        """
        Save a cycle report.

        Args:
            cycle_id: Unique identifier for the cycle.
            cycle_data: Data to be stored for the cycle.
        """
        self._cycles[cycle_id] = cycle_data

    def get_cycle(self, cycle_id):
        """
        Retrieve a cycle report by its ID.

        Args:
            cycle_id: Unique identifier for the cycle.

        Returns:
            The cycle data if found, None otherwise.
        """
        return self._cycles.get(cycle_id)

    def list_cycles(self):
        """
        List all stored cycle reports.

        Returns:
            A list of cycle IDs.
        """
        return list(self._cycles.keys())

    def delete_cycle(self, cycle_id):
        """
        Delete a cycle report by its ID.

        Args:
            cycle_id: Unique identifier for the cycle.
        """
        if cycle_id in self._cycles:
            del self._cycles[cycle_id]

    def count(self):
        """
        Count the number of stored cycle reports.

        Returns:
            The number of cycles stored.
        """
        return len(self._cycles)