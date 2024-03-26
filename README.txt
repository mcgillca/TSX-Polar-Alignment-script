IMPORTANT:

For Linux users, the install script will copy the files into /usr/local/bin and
the icon files into /usr/share/pixmaps. Before running the install script, you
MUST edit the PAUI.py file - otherwise the data for my setup will be stored
in the script.

The install script will also create a desktop icon and put the script into the
Education menu.

For Mac and Windows users, you can run the tool by typing: python3 PAUI.py

Before use, edit the following pieces of data near the top
of the PAUI file:

Image exposure data:

CAM_DURATION: how long you need for each picture. This should be just long
enough to plate solve. It will also determine how long between updates of
your alignment.

CAM_BINNING: the binning you require for plate solving. You can generally
get away with a highish bin, and that speeds up downloads and frequency of
upates of your aligment.

CAM_SCALE: the arcsec/pixel of your binned image - used for platesolving

CAM_FILTER: set this to the name of the filter if you want to specify one
for platesolving e.g. CAM_FILTER = "Lum". If left set to "", will not
attempt to set the filter, so leave this blank if you don't have a filter
wheel.

Image location data:

PA_DEC: the script takes two images at the same DEC to work out the
polar alignment.  Chose a DEC where you can see the sky from your
location, but also sufficiently far from the pole that the locations have
a good separation on the sky. Choosing e.g. DEC of 80 will mean that
the locations are too close to get an accurate estimate of your alignment,
though the routine will try!.

HA1 and HA2: the hour angles for where to take images. Make sure these are
on the same side as the meridian if your scope does a meridian flip. Make
sure that the (HA2, DEC) position is NOT close to the zenith, nor close
to the east-west axis. The script tries to evaluate rotations around both
these axes and if you are close to the axis, it is hard for the script
to work out what the roation should be (if you are exactly on the zenith for
example, any azimulthal rotations would not change the position of the image,
just its orientation). The (HA1, DEC) may be close to the zenth or
east-west axis.

Aim of the script

The aim of the script is to get you close enough to polar alignment that
after running a Tpoint model, the star you choose for accurate polar alignment
remains in the field of view. Suggested workflow is:

1) Disable tpoint pointing corrections
2) Run the script
3) Re-enable tpoint pointing corrections
4) Run tpoint (re)calibration model
5) Use accurate polar alignment.

Since the script and Tpoint only need to be able to plate solve, this
procedure can be carried out before nautical dusk.

In practice, I have found that starting from a few degrees from polar alignment,
I only try to get within about 10 arc mins of the pole. If I start the
alignment again at this point, the difference from the previous run is again
about 10 arc minutes, but the sign of the change is often different, an
indication of the likely size of the error. However, if I then polar align
and try to get close to zero starting from from this much closer location,
I can then get to within 2 arc minutes of pole as confirmed by Tpoint, so you
can use the script to get accurate alignment even without Tpoint.

Running the Script

Before running the script, you must disable the Tpoint pointing corrections.
Otherwise, the script will try and get you bac to your previous polar
alignment point. 

You must also have TSX running and have enabled the TCP server (under the
TSX tools menu). The script will tell you if this is not the case.

After running the script, click the Start button. This will first remind
you to disable the Tpoint corrections.

Once you have confirmed that the pointing corrections are disabled, the script
will then attempt to take two images at the Declination and hour
angles as specified above. From this, it can calculate the position of the
telescope axis and will indicate how much to raise or lower and rotate
the mount. Only use the altitude and azimuthal adjustment mechanisms. The
rotation follows the Tpoint convention - it is clockwise or anticlockwise
as seen from above your mount.

Do NOT move the telescope position - just let the mount track normally.

The script will then take and platesolve regular images to update the position.
If you move adjust the mount, it is likley that one or two images cannot be
plate solved - just wait for a couple of seconds and this will be resolved
(unless you are unlucky with clouds, but...)

You do not need to try for perfection - anything within 5 arc mins is likely
to be good enough for imaging if you are guiding - polar alignment only
prevents field rotation for guided images. Unguided imaging may require better
alignment, but your highest accuracy will be provided by Tpoint and the
standard TSX accurate alignment routines once this script has you close enough.

Once you are close enough, click "Stop" - the script will complete taking
its final image and then stop (this prevents TSX from crashing).

You can click Start again if desired - this will create a fresh
measurement of your polar alignment, but do not expect this to be exactly
the same. The script does not account for e.g. scope flexure and refraction
which will limit the accuracy that can be achieved.

Clear will clear the current display text.

Changelog
V 1.0  - Initial release
V 1.1  - Tidied up interface. Added scrollbar and clear button.
V 1.2  - Added the abilty to define a filter to be used with plate solving.
         Now removes the image and SRC files by default.
	 Binning and filter wheel positions are restored after the run

