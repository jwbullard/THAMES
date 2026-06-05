THAMES 1.0.0-alpha.3 - Alpha Release Notes
=============================================

This is a working draft. Append entries as fixes land; finalize at release time.

Fixed since alpha-2
  1. Mix Design: small system sizes (25-49) now accepted.
     Alpha-2 had a stale schema constraint that silently rejected any
     system_size value below 50 in the Mix Design panel. The "Generate"
     click appeared to do nothing - an empty operation folder was
     created but no input file was written and micgen never launched.
     The only evidence was a buried "Error auto-saving mix design"
     line in thames.log. The legacy system_size field is now bounded
     25-400 to match the per-axis system_size_x/y/z fields.
     Workaround on alpha-2: use a system size of 50 or larger.

Added since alpha-2
  (none yet)

Changed since alpha-2
  (none yet)

Known Limitations
  (carry forward applicable items from alpha-2 at release time;
  remove items that have been fixed in this release)
