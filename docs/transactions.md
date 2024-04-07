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

