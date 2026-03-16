# POS Returns and Batch Policy

## Return validation

- **Item-level:** Total return quantity per item cannot exceed the total quantity sold for that item on the original invoice. This is enforced by `validate_return_items()`.
- **Batch-level:** POS Next does **not** require the returned batch to match the batch that was sold. Returns are validated by item code and quantity only.

## Return invoices without a source invoice

When creating a return invoice **without** linking to an original invoice (`return_against` is not set):

- For batch-tracked items, batch numbers are auto-assigned by `_auto_set_return_batches()`.
- Only **non-expired** and **enabled** batches with available quantity in the selected warehouse are considered.
- Batches are chosen in FIFO order (first to expire, first out).

## Return invoices with a source invoice

When creating a return **against** an original invoice (`return_against` is set):

- `validate_return_items()` ensures return qty per item does not exceed the remaining returnable qty from that invoice.
- Batch numbers can be chosen by the user or left for auto-assignment; they do not have to match the original invoice’s batches.

## Batch selection for sales (add to cart)

- `get_batch_serial_details()` and `get_item_detail()` only show batches that:
  - Have stock in the POS warehouse (warehouse-scoped),
  - Are not expired,
  - Are not disabled.
- Batches are sorted by expiry (FIFO) so the cashier is guided to sell the soonest-expiring stock first.
