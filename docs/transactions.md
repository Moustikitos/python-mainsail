<a id="mainsail.transaction"></a>

# Module mainsail.transaction

<a id="mainsail.transaction.SKIP_SIG1"></a>

#### mainsail.transaction.SKIP\_SIG1

skip signature mask.

<a id="mainsail.transaction.SKIP_SIG2"></a>

#### mainsail.transaction.SKIP\_SIG2

skip second signature mask.

<a id="mainsail.transaction.SKIP_MSIG"></a>

#### mainsail.transaction.SKIP\_MSIG

skip multiple signatures mask.

<a id="mainsail.transaction.Transaction"></a>

## Transaction Objects

```python
class Transaction()
```

Generic transaction class.

<a id="mainsail.transaction.Transaction.APB_MODE"></a>

#### Transaction.APB\_MODE

TODO: continue APB_MODE dev

<a id="mainsail.transaction.Transaction.export"></a>

### Transaction.export

```python
def export() -> dict
```

Return a mapping representation of the transaction.

<a id="mainsail.transaction.Transaction.serialize"></a>

### Transaction.serialize

```python
def serialize(skip_mask: int = 0b000) -> str
```

Serialize the transaction.

**Arguments**:

- `skip_mask` _int_ - binary mask to skip signatures during the
  serialization. Available masks are `SKIP_SIG1`, `SIG_SIG2` and
  `SIG_MSIG`.
  

**Returns**:

- `str` - the serialized transaction as hexadecimal string.

<a id="mainsail.tx"></a>

# Module mainsail.tx

<a id="mainsail.tx.deserialize"></a>

## deserialize

```python
def deserialize(serial: str) -> Transaction
```

Build a transaction from hexadecimal string.

**Arguments**:

- `serial` _str_ - the serialized transaction as hexadecimal string.
  

**Returns**:

- `Transaction` - the transaction.
  

**Raises**:

- `AttributeError` - if transaction builder is not defined.

