# Simulation model

Discrete timestep: 0.25 simulated seconds. The wall-clock service schedules ticks; elapsed wall time never changes a tick's distance or outcome. Under CPU load the display may run slower than real time, never skip physical time. The browser receives snapshots at 4 Hz.

Tasks execute in JSON order for each assigned UAV. Pending → en route → in progress → completed. A movement tick consumes a distance budget `speed × dt` across as many waypoints as needed. Heading is measured clockwise from north. On arrival, service starts; subsequent ticks accrue service time. Motion remaining in the arrival tick is not reused as service time. Next tasks dispatch on the next tick. When every task completes, the mission stops.

Route validation uses Shapely polygon buffers of 12 m and tests full route segments, not waypoint samples. Buildings, debris, blocked roads and prohibited airspace are hard obstacles in this conservative 2D abstraction. Flood polygons allow aerial overflight. No A\*, route optimization or UAV collision avoidance is claimed. Hard obstacles and fixed routes are never modified during a run.

Battery decreases by distance × 0.002 percentage points, clamped at zero. Default routes have ample initial battery; low-battery policy and return-to-base are deferred. There is no energy expenditure during point service in this simple model. Task progress is service time, not area coverage.

Seed 42 is reproducibility metadata, not an active random stream. Event IDs are monotonic integers within the run. Transport revision survives reset, while world tick and event sequence restart deterministically.
