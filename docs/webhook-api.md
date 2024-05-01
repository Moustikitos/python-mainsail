<a id="mainsail.webhook"></a>

# webhook

<a id="mainsail.webhook.condition"></a>

## condition

```python
def condition(expr: str) -> dict
```

Webhook condition builder from `str` expression.

<style>td,th{border:none!important;text-align:left;}</style>
webhook                   | expr
------------------------- | ------------
`lt` / `lte`              | `<` / `<=`
`gt` / `gte`              | `>` / `>=`
`eq` / `ne`               | `==` / `!=`
`truthy` / `falsy`        | `?` / `!?`
`REGEXP` / `contains`     | `\` / `$`
`between` / `not-between` | `<>` / `!<>`


```python
>>> from mainsail import webhook
>>> webhook.condition("vendorField\^.*payroll.*$")
{'value': '^.*payroll.*$', 'key': 'vendorField', 'condition': 'regexp'}
>>> webhook.condition("amount<>2000000000000:4000000000000")
{'value': {'min': '2000000000000', 'max': '4000000000000'}, 'condition': 'between', 'key': 'amount'}
```

**Arguments**:

- `expr` _str_ - human readable expression.
  

**Returns**:

- `dict` - webhook conditions

