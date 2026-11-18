# Measured cement PSDs recovered from VCCTL 9

Recovered 2026-11-17. Each `<name>.psd` file is the measured particle size
distribution VCCTL stored for a cement: one line per size class, diameter (µm)
then volume fraction, whitespace-separated, exactly as stored.

`vcctl_cement_psd_map.csv` lists which PSD file each VCCTL cement used (VCCTL's
`CEMENT.PSD` column).

## Source

- VCCTL 9's Apache Derby database `data/database/vcctl_cement` in the
  `~/Code/VCCTL` repository (github.com/jwbullard/VCCTL), table `DB_FILE`,
  rows with `TYPE = 'psd'` (31 files).
- Read from the version **before** commit `f2eb05a0` ("Updating particle shape
  data"). That commit removed Derby's `seg0/cd1.dat` (a system index), so the
  database at that commit and later cannot be opened.
- Read on a copy with Derby 10.10 (`web/WEB-INF/lib/derby.jar`,
  `derbytools.jar`) and `SYSCS_UTIL.SYSCS_EXPORT_QUERY_LOBS_TO_EXTFILE`.

## Notes

- `ustype1` used `cement151 psd` in VCCTL.
- VCCTL's `ma178` row points at `cement151 psd`, but THAMES's `ma178` matches
  VCCTL's own `ma178 psd` file, which is kept here.
- `dh`, `cementhoc`, `cementotc` and `cementrci` name PSD files (`dh psd`, ...)
  that are not in VCCTL's database; their data must come from other archives.
- Migration `20261117_04_vcctl_measured_psd` gives `ustype1`, `cement116`,
  `cement168` and `sacci-425` these measured tables in THAMES (alpha-4.3).
