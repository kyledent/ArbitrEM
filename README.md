# ArbitrEM
SerialEM scripts for single-particle cryoEM data-collection *ad arbitrium*. Strong familiarity with SerialEM scripting is advised as this code is currently in 'alpha'. This README is currently under construction, and a detail user guide is still to be released. May the, uh, Coulomb potential, be with you...

## Overview
The ArbitrEM workflow enables the user to collect targeted micrograph exposure movies. To allow this, foil-holes or regions of lacey specimen grids must be tracked during each of two the phases of data-collection: low-magnification view-map acquisition for targeting (the *AcquireHoleViewMaps.txt* or *AcquireLaceyViewMaps.txt* scripts), and high-magnification view-map tracking for data-acquisition, by the *ArbitrEM.txt* script), typically with a dose per exposure of 0.02 - 0.04 e<sup>-</sup>/Å<sup>2</sup>, during which up to 10 neighbouring holes may also be exposed depending on the specimen-foil geometry, and as a consequence, the total number of exposures must be kept to a minimum to preserve high-resolution information. Relatively low magnification ‘view-maps’ (derived from images recorded using the SerialEM low-dose (LD) ‘View’ imaging preset) are acquired so that specific regions on the specimen mesh can be targeted with an accuracy of up to ± 30 nm using a series of beam-image shift displacements of up to 2.5 µm calculated per view-map. Accurate targeting is achieved by taking into account the offset of the specimen stage re-alignment. 

The workflow involves microscope setup/specimen grid identification in the morning, with view-map acquisition until mid-afternoon (~100 per hour). At present, target selection is performed at the microsope within SerialEM (although a 'dummy' SerialEM installation can be setup at an offline Windows terminal). Movie acquisition rates are typically between 80-100 micrographs per hour when using the Gatan K2 Summit when a navigator describes on average two acquistions per view-map.

## Stage 1: Acquisition of View-maps for target selection
During development of the scripts a Titan Krios equipped with Gatan K2/GIF was used (Krios IV, eBIC, Diamond Light Source). The workflow first involved acquisition of grid-square montages (e.g. a 3x3 tiled montage at a nominal magnification of 2250X, ~62 Å/pixel sampling, ~23 µm<sup>2</sup> field-of-view per tile using 20% overlap allowed coverage of a typical ‘300 mesh’ grid-square). These grid-square montages allowed holes of desirable ice thickness and sample content to be identified, and using standard SerialEM navigator functions the holes of interest were then selected using a grid-of-points created using the corresponding function used in conjunction with the ‘polygon’ Navigator tool within SerialEM. The Navigator stage coordinate ‘registration’ was then updated to align these points with their respective specimen holes in the LD-View mode; this to account for a small difference in apparent specimen position between Grid-square montage and View magnifications. 

At hole view-map magnification (11000-15000X, ~13 Å/pixel, i.e. ~5 µm<sup>2</sup> field-of-view, with a 12 µm illumination diameter) a specimen hole template image was acquired using the HoleViewTemplate script after exposure time and defocus were assessed to ensure adequate contrast was available for target discrimination and selection; these parameters are varied depending on the contrast required and thickness of the ice layer, for this study an exposure time of 2 seconds and a defocus of 75 µm were applied. A series of view-map images were then automatically acquired across specimen-grid using a SerialEM script AcquireHoleViewMaps at a rate of ~100 holes/hour. The detector readout was cropped for the LD-View preset to ensure that areas from neighbouring holes did not appear in the template as these would interfere with cross-correlation based hole alignment. During this process, each hole is approximately centred using stage-shift only in a single re-alignment step (a total of two exposures per hole) by cross-correlation against a template image and converted into a SerialEM anchoring/re-alignment maps. 

## Stage 2: Targeted exposure movie acquisition.

### a - Target selection
Tubes of interest were identified, and the high-magnification acquisition points marked at the site of interest on each of the anchor maps making sure that the acquisition illuminations do not overlap into the recorded area (boxes). 

### b - SerialEM/ArbitrEM session setup
Download the ArbitrEM scripts onto a support workstation running Linux. A Python script (*processNavigator.py*) is run to compile the information contained within the SerialEM navigator for use during the automated data-collection as well as to specify the settings (such as defocus range) to be used for the data-collection. When running the script on a navigator file, please make sure that all polygons, medium magnification montages and view-map acquisition points have been removed from the navigator. A future release of *processNavigator.py* will automatically ignore these, but for the time being its important to clean the navigator after areas of interest have been targeted.

Run *processNavigator.py* as follows:

```
processNavigator.py --nav navigator.nav --d 5 --sessionBasePath "D:\mysession" [--v]                                                   
```

Above a navigator file *navigator.nav* is specified, prepared using view-maps of diameter *d* and a SerialEM session base-path *D:\mysession* have been specified.

The script will by default create a directory called arbitrEM with the following contents:

    - ./arbitrEM/runArbitrEM.txt - open this within the SerialEM script panel and review the settings to ensure they are correct.
    - ./arbitrEM/indexGuide.txt
    - ./arbitrEM/pointIndices.txt
    - ./arbitrEM/settings/defocus.txt
    - ./arbitrEM/settings/early_return.txt
    - ./arbitrEM/settings/customOffset.txt

Transfer the arbitrEM folder into the session folder on the SerialEM control PC.

## General notes

### On the targeting calculation
*processNavigator.py* will associate each acquisition point with its corresponding view-map based on proximity of stage coordinates and in consideration of the hole/map diameter and output a series of indices which allow the ArbitrEM SerialEM script to interpret the navigator efficiently on-the-fly. For example, for the R2/1 specimens grids used the actual hole diameter was measured to be 2.7 µm (with a measured centre-to-centre distance: 3 µm). In that case we choice a  '--d' of 2.8 µm and autofocused every hole at a displacement of 1.7 µm along the tilt-axis. The final step is to calibrate the offset in apparent specimen position between the SerialEM LD-View and LD-Record presets. 

During automated data-collection each foil-hole is revisited using the anchor maps to perform realignment of the specimen stage to within an accuracy (± 75 nm); also within a single refinement step, i.e. two tracking exposures per hole, but with half the exposure time used to acquire the hole-view maps used for targeting to limit the total pre-dose to 0.5 - 1.2 e-/Å<sup>2</sup>.  The stage XY offset of the revisited position from the original position of hole-view map is noted and the targeting beam-image shift calculated as: (𝚫x,𝚫y)<sub>n</sub> = APstage(X,Y)<sub>n</sub>  - Oc(x,y) - V<sub>r</sub>stage(X,Y) – V<sub>t</sub>stage(X,Y); where, for n acquisition points (AP) for a particular targeting view-map (V<sub>t</sub>), and V<sub>r</sub> is the revisited view-map image, O<sub>c</sub>(x,y) is the offset supplied by the microscope user. The high-magnification exposure movies are then automatically recorded for each view-map (e.g. 130000X, 1.05 Å/pixel) by the ArbitrEM script after appropriate delays for stage-shift and image-shift (5 seconds and 3 seconds, respectively). Auto-focusing was performed once per hole, implying a stage-shift delay of at least 15 seconds. A parameter allowing for a custom offset is provided (O<sub>c</sub>) to allow any systematic errors in targeting to be corrected on-the-fly and should compensate for any changes to the offset between LD-view and LD-record that could possibly arise, for example, owing to lens hysteresis. The custom offset is likely to be more relevant to the Thermo Fisher Scientific Talos/Galcios systems which feature constant power lenses for the objective lens only. 

### A note on targeting performance
On a Thermo Fisher Scientific Talos Arctica, ArbitrEM has been demonstrated to function with an accuracy of ±75 nm (defocus of -75 um for the LD-View preset). The Artica, employing a two-condenser lens illumination system does not conveniently enable parallel illumination at both View-Map (LD-View) and Acquisition (LD-Record) magnifications. On the Titan Krios, an accuracy of 30 nm is enabled by the parallel illumination for both imaging presets. These scripts are still under development and further statistics will become available over time.



