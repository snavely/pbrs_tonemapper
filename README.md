This rendering code accompanies the paper

```
CGIntrinsics: Better Intrinsic Image Decomposition through Physically-Based Rendering
Zhengqi Li and Noah Snavely
ECCV 2018
```

# Rendering with Mitsuba

We modified the Mitsuba rendering settings compared to the original
PBRS settings. In particular, we dramatically increased the number of
samples per pixel, and switched to using a bidirectional path tracing
integrator.

We have included an example Mitsuba input XML file,
main_template_color_rgb.xml, to illustrate these changes. This file
corresponds to scene 0004d52d1aeeb8ae6de39d6bd993e992 in SUNCG/PBRS.

# Tonemapping

The script tonemap_rgbe.py can be used to tonemap a .rgbe image
produced by Mitsuba using the method described in the paper. In
particular, we used the following settings:

  > tonemap_rgbe.py --input_image foo.rgbe --output_image foo.png --percentile 90 --percentile_point 0.80
