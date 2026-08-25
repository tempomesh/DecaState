class DecaStateError(Exception): pass
class StateNotFoundError(DecaStateError): pass
class StateCorruptError(DecaStateError): pass
class FingerprintMismatchError(DecaStateError): pass
class RuntimeUnsupportedError(DecaStateError): pass
class RestoreUnsupportedError(DecaStateError): pass
class BridgeUnavailableError(DecaStateError): pass
class UnsafeMigrationError(DecaStateError): pass
