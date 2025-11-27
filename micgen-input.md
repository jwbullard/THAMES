Nov 24, 2025

# Order of Input

1. Random number seed (negative integer)
2. SPECSIZE (2)
3. X_size (voxels)
4. Y_size (voxels)
5. Z_size (voxels)
6. Image_resolution (micrometers)
7. If aggregate slab must be added, ADDAGG (3); else go to item 8 below
8. ADDPART (4)
9. Add all spheres, (0), all real-shape (1), or mixed (2) particles
	1. If real shape or mixed:
		1. Absolute path to shape directory (with final separator added)
		2. Name of specific shape set (no separator at beginning or end)
		3. Go to item 10 below
	2. If spheres, go straight to item 10
10. PC clinker volume fraction (even if it is zero)
11. Combined volume fraction of all non-clinker solid powders
12. Volume fraction of electrolyte
13. Volume fraction of void (this is not air content for concrete)
14. Total number of distinct solid phases (including each clinker phase) to add
15. For each distinct solid phase
	1. Phase id number
	2. Volume fraction of this phase on total solids basis
	3. Number of particle size classes for this phase
	4. For each size class of this phase
		1. enter diameter of that size class in voxel units
		2. enter volume fraction of this phase in that size class
	5. If item 8 above specified mixed (2), enter whether this phase is sphere (0) or real shape (1), otherwise go to item 15 below
	6. Only if this phase is real shape, do next 2, otherwise go to item 16 below
		1. shape path with final separator
		2. name of the specific shape set for this phase (no separator before or after)
16. Dispersion factor (0 for random, 1, or 2)
17. If flocculation requested, FLOCC (5), then
	1. Degree of flocculation (0.0 to 1.0)
18. If PC clinker volume fraction in item 10 above > 0, DISTRIB (6); else go to item 19 below
	1. Path/root name of correlation function files for this clinker
	2. volume fraction of alite
	3. surface fraction of alite
	4. volume fraction of belite
	5. surface fraction of belite
	6. volume fraction of aluminate
	7. surface fraction of aluminate
	8. volume fraction of ferrite
	9. surface fraction of ferrite
	10. volume fraction of arcanite
	11. surface fraction of arcanite
	12. volume fraction of thenardite
	13. surface fraction of thenardite
19. If need to add void phase, ADDVOID (7), otherwise go to item 20 
20. ONEVOX (9)
21. OUTPUTMIC (10)
	1. Name of microstructure file to create
	2. Name of particle id structure file to create
22. EXIT (1)