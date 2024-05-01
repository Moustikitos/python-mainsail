<a id="mainsail.identity"></a>

# identity

This modules provides cryptographic primitives to interact with blockchain.

```python
>>> from mainsail import identity
```

<a id="mainsail.identity.KeyRing"></a>

## KeyRing Objects

```python
class KeyRing(cSecp256k1.KeyRing)
```

Subclass of `cSecp256K1.KeyRing` allowing secure filesystem saving and
loading. It is also linked to mainsail network configuration to select
appropriate Schnorr signature specification (bcrypto 4.10 or BIP 340) to be
applied.

```python
>>> import os
>>> signer = identity.KeyRing.create(int.from_bytes(os.urandom(32)))
>>> signer  # KeyRing is a subclass of builtin int
40367812022907163119325945335177282621496014100307111368749805816184299969919
>>> sig = signer.sign("simple message")
>>> puk = signer.puk()  # compute associated public key
>>> signer.verify(puk, "simple message", sig)
True
>>> type(signer)  # bcrypto 4.10 specification used
<class 'mainsail.identity.Bcrpt410'>
```

<a id="mainsail.identity.KeyRing.dump"></a>

### KeyRing.dump

```python
def dump(pin: Union[bytes, List[int]]) -> None
```

Securely dump `KeyRing` into filesystem using pin code. Override
existing file if any.

**Arguments**:

- `pin` _bytes|List[int]_ - pin code used to _encrypt KeyRing. Pin code
  may be a list of short (0 < int < 255) or a bytes string.
  
```python
>>> signer.dump([0, 0, 0, 0])  # dump into filesystem using pin 0000
>>> signer.dump(b"\x00\x00\x00\x00")  # equivalent
```

<a id="mainsail.identity.KeyRing.load"></a>

### KeyRing.load

```python
@staticmethod
def load(pin: Union[bytes, List[int]])
```

Securely load KeyRing from filesystem using pin code.

**Arguments**:

- `pin` _bytes|List[int]_ - pin code used to _encrypt KeyRing. Pin code
  may be a list of short (0 < int < 255) or a bytes string.
  

**Returns**:

- `Schnorr|Bcrpt410` - signer object.
  
```python
>>> identity.KeyRing.load([0, 0, 0, 0])
40367812022907163119325945335177282621496014100307111368749805816184299969919
>>> identity.KeyRing.load(b"\x00\x00\x00\x00")
40367812022907163119325945335177282621496014100307111368749805816184299969919
```

<a id="mainsail.identity.KeyRing.create"></a>

### KeyRing.create

```python
@staticmethod
def create(obj: int = None)
```

Create a `KeyRing` signer subclass with the appropriate schnorr
signature specification.

**Arguments**:

- `obj` _int_ - the value of the private key.
  

**Returns**:

- `Schnorr|Bcrpt410` - signer object.

<a id="mainsail.identity.get_signer"></a>

## get\_signer

```python
def get_signer()
```

Returns the the network appropriate signer.

<a id="mainsail.identity.bip39_hash"></a>

## bip39\_hash

```python
def bip39_hash(secret: str, passphrase: str = "") -> bytes
```

Returns bip39 hash bytes string. This function does not check mnemonic
integrity.

**Arguments**:

- `secret` _str_ - a mnemonic string.
- `passphrase` _str_ - salt string.
  

**Returns**:

- `bytes` - 64 length bytes string.

<a id="mainsail.identity.sign"></a>

## sign

```python
def sign(data: Union[str, bytes],
         prk: Union[KeyRing, List[int], str, int] = None,
         format: str = "raw") -> str
```

Compute Schnorr signature from data using private key according to bcrypto
4.10 spec or BIP340 specification. Signature format is RAW by defaul but
can also be specified a DER.


```python
>>> prk = identity.KeyRing.load([0,0,0,0])
>>> identity.sign("simple message", [0, 0, 0, 0])
'5993cfb3d7dafdfe58a29e0dfc9ef332acc7bb1429ba720b20e7ea6b4a961dd0026ed229f5095581188816bf120bcad0d25cdada03a3add04bd539ab2ba3becb'
>>> identity.sign("simple message", prk)
'5993cfb3d7dafdfe58a29e0dfc9ef332acc7bb1429ba720b20e7ea6b4a961dd0026ed229f5095581188816bf120bcad0d25cdada03a3add04bd539ab2ba3becb'
>>> identity.sign("simple message", 40367812022907163119325945335177282621496014100307111368749805816184299969919)
'5993cfb3d7dafdfe58a29e0dfc9ef332acc7bb1429ba720b20e7ea6b4a961dd0026ed229f5095581188816bf120bcad0d25cdada03a3add04bd539ab2ba3becb'
>>> identity.sign("simple message", prk, "der")
'304402205993cfb3d7dafdfe58a29e0dfc9ef332acc7bb1429ba720b20e7ea6b4a961dd00220026ed229f5095581188816bf120bcad0d25cdada03a3add04bd539ab2ba3becb'
```

**Arguments**:

- `data` _str|bytes_ - data used for signature computation.
- `prk` _KeyRing|List[int]|str|int_ - private key, keyring or pin code.
- `format` _str_ - `raw` or `der` to determine signature format output.
  

**Returns**:

- `str` - Schnorr signature in raw format (ie r | s) by default.

<a id="mainsail.identity.user_keys"></a>

## user\_keys

```python
def user_keys(secret: Union[int, str]) -> dict
```

Generate keyring containing secp256k1 keys-pair and wallet import format
(WIF).

**Arguments**:

- `secret` _str|int_ - anything that could issue a private key on secp256k1
  curve.
  

**Returns**:

- `dict` - public, private and WIF keys.

<a id="mainsail.identity.wif_keys"></a>

## wif\_keys

```python
def wif_keys(seed: bytes) -> Union[str, None]
```

Compute WIF key from seed.

**Arguments**:

- `seed` _bytes_ - a 32 length bytes string.
  

**Returns**:

- `str` - the WIF key.

