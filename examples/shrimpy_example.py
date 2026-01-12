"""Example of using ome_writers with useq.MDASequence and pymmcore-plus."""

from pathlib import Path

import numpy as np
import shutil
import time

import ome_writers as omew

try:
    import useq
except ImportError as e:
    raise ImportError(
        "This example requires useq-schema. Please install it via "
        "pip install useq-schema"
    ) from e

try:
    from pymmcore_plus import CMMCorePlus
    from pymmcore_plus.metadata import FrameMetaV1
except ImportError as e:
    raise ImportError(
        "This example requires pymmcore-plus. Please install it via "
        "pip install pymmcore-plus"
    ) from e

# --------------------------CONFIGURATION SECTION--------------------------#

# Create a MDASequence
# NOTE: axis_order determines the order in which frames will be appended to the stream.
# seq = useq.MDASequence(
#     axis_order="ptcz",
#     stage_positions=[(0.0, 0.0), (10.0, 10.0)],
#     time_plan={"interval": 0.1, "loops": 3},
#     channels=["DAPI", "FITC"],
#     z_plan={"range": 2, "step": 1.0},
# )

seq = useq.MDASequence(
    channels=[
        {"config": "DAPI", "exposure": 2},
        {"config": "FITC", "exposure": 10},
    ],
    stage_positions=[
        {"x": 0, "y": 0, "name": "Pos0"},
        {"x": 1, "y": 1, "name": "Pos1"},
        {"x": 0, "y": 1, "name": "Pos2"},
        {"x": 1, "y": 0, "name": "Pos3"},
    ],
    time_plan={"interval": 0.66, "loops": 3},
    z_plan={"range": 10, "step": 0.2},
    axis_order="tpcz",
)
# -------------------------------------------------------------------------#

# Initialize pymmcore-plus core and load system configuration
core = CMMCorePlus.instance()
core.loadSystemConfiguration()
core.setProperty("Camera", "OnCameraCCDXSize", "2048")
core.setProperty("Camera", "OnCameraCCDYSize", "256")
core.setProperty("Z", "UseSequences", "Yes")


# Convert the MDASequence to ome_writers dimensions
dims = omew.dims_from_useq(
    seq, image_width=core.getImageWidth(), image_height=core.getImageHeight()
)

# Choose backend: acquire-zarr, tensorstore, or tiff
backend = "tiff"
data_dir = Path("~/Documents/test/test_14_tiff_512x2048").expanduser()
if not data_dir.exists():
    data_dir.mkdir(parents=True)
else:
    shutil.rmtree(data_dir)

# Create an stream using the selected backend
ext = "tiff" if backend == "tiff" else "zarr"
path = data_dir / f"{ext}_example.ome.{ext}"
stream = omew.create_stream(
    path=str(path),
    dimensions=dims,
    dtype=np.uint16,
    backend=backend,
    overwrite=True,
    position_keys=["Pos0", "Pos1", "Pos2", "Pos3"],
)

# Append frames to the stream on frameReady event
@core.mda.events.frameReady.connect
def _on_frame_ready(
    frame: np.ndarray, event: useq.MDAEvent, frame_meta: FrameMetaV1
) -> None:
    stream.append(frame)


# Flush and close the stream on sequenceFinished event
@core.mda.events.sequenceFinished.connect
def _on_sequence_finished(sequence: useq.MDASequence) -> None:
    stream.flush()
    print("Data written successfully to", path)


# Start the acquisition
start_time = time.time()
core.mda.run(seq)
end_time = time.time()
print(f"Time taken: {end_time - start_time} seconds")
