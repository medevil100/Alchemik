class HistoryRepository:
    """Właściciel kontraktu trwałości dla cykli, MarketEvent i Observation."""

    def __init__(self):
        self._cycles = {}
        self._observations = {}
        self._readings = {}

    # ------------------------------------------------------------------
    # Kontrakt trwałości InstrumentReading / InstrumentObservation
    # ------------------------------------------------------------------

    def save_reading(self, observation, reading) -> str:
        """
        Atomowo zapisz InstrumentObservation i InstrumentReading.

        Otrzymuje istniejącą lub nowo utworzoną Observation (pierwszy argument)
        oraz Reading do zapisania (drugi argument). Repozytorium zapisuje oba
        atomowo; nie tworzy Observation samodzielnie.

        Zwraca dokładnie jeden z czterech wyników:
          * ``ACCEPTED``       — nowy fakt zapisany, Observation zaktualizowana
          * ``DUPLICATE_NO_OP`` — identyczny fakt już istnieje, bez zmian
          * ``CONFLICT``       — ta sama tożsamość, inna treść;
                                  Observation → INTEGRITY_BREACHED
          * ``STALE_TIMESTAMP``— starszy timestamp, odrzucony bez naruszenia
                                  integralności
        """
        instrument_id = observation.instrument_id
        identity = (instrument_id, reading.market_data_timestamp)

        # Check for existing reading with same identity
        existing = self._readings.get(identity)
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
            if same_content:
                return "DUPLICATE_NO_OP"
            else:
                observation.terminate("INTEGRITY_BREACHED", "Content conflict")
                self._observations[instrument_id] = observation
                return "CONFLICT"

        # Check for STALE_TIMESTAMP
        for stored_rdg in self._readings.values():
            if stored_rdg.instrument_id == instrument_id:
                if reading.market_data_timestamp < stored_rdg.market_data_timestamp:
                    return "STALE_TIMESTAMP"

        # Determine prev_reading_id
        prev_reading_id = None
        instrument_readings = [
            r for r in self._readings.values()
            if r.instrument_id == instrument_id
        ]
        if instrument_readings:
            latest_rdg = max(instrument_readings, key=lambda r: r.market_data_timestamp)
            prev_reading_id = latest_rdg.reading_id

        # Store observation
        self._observations[instrument_id] = observation

        # Store reading
        self._readings[identity] = reading
        return "ACCEPTED"

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
        zaakceptowanym Readingiem (wg największego market_data_timestamp).

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
            latest = max(instrument_readings, key=lambda r: r.market_data_timestamp)
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