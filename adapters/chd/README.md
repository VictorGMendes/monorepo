# BSC RPA CHD Adapter

## TODO

- Refactor this a bit to be closer to what Astra adapter is; It's approach is better and more intuitive
- ChdPage.uncheck_enabled_checkboxes loops while .count() > 0. Change this to .is_visible() or something like that
- Insert this function somewhere:

```python
# Utils


def select_option_by_text_start(
    select_control: Locator,
    text_start: str,
    timeout: float | None = None,
    no_wait_after: bool | None = None,
    force: bool | None = None,
) -> None:
    """Selects the first option in the select element whose text starts with **text_start**"""
    option_value = (
        select_control.locator("option")
        .get_by_text(re.compile(f"^{text_start}"))
        .first.get_attribute("value")
    )
    select_control.select_option(
        value=option_value, timeout=timeout, no_wait_after=no_wait_after, force=force
    )
```
