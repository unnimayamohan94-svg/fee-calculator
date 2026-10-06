BROWSER-ONLY VERSION
Open index.html directly. It is fully self-contained.

CHANNELS
- MFloos: existing behavior.
- KJ: Kuraimi Express, subtle gold theme.

KJ YER:
Same liquidity calculation as MFloos YER.

KJ SAR/USD:
Uses only FEE_DETL.LQDTY = 00004 (No Liquidity).
If there is no valid 00004 amount-range row, the app shows:
"Fee configuration missing for the selected Product, Transaction, Currency and Amount."

Extra Commission:
Amount * (Sender Zone % - Receiver Zone %) / 100.
If raw value is zero or negative, applied Extra Commission is 0.
Total Fee = Transaction Fee + Extra Commission.
