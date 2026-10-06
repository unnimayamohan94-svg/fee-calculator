FLASK + SQLITE VERSION

Mac:
  chmod +x run_mac_linux.sh
  ./run_mac_linux.sh

Windows:
  run_windows.bat

Open:
  http://127.0.0.1:5000

CHANNELS
MFloos:
- Existing MFloos logic preserved.
- YER = liquidity calculation.
- SAR/USD = LQDTY 00001 High Fee + Extra Commission.

KJ:
- Product: Kuraimi Express.
- YER = same liquidity calculation as MFloos.
- SAR/USD = ONLY LQDTY 00004 (No Liquidity) + Extra Commission.
- Missing valid 00004 amount-range row returns:
  Fee configuration missing for the selected Product, Transaction, Currency and Amount.

Extra Commission:
Amount * (Sender Zone % - Receiver Zone %) / 100.
If result <= 0, applied Extra Commission = 0.
