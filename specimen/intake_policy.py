from specimen.frame import MeasurementFrame


class RegistrationConflict(ValueError):
    pass


def should_create_trial(
    trial_id: str,
    current: MeasurementFrame | None,
    requested: MeasurementFrame,
) -> bool:
    if current is None:
        return True
    if current != requested:
        raise RegistrationConflict(f'measurement frame is already fixed for {trial_id!r}')
    return False
