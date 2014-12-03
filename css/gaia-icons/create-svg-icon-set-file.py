#!/usr/bin/env python

# Experimental config option:
#
# Right now Mozilla only supports a CSS trick which stacks all of the icons on
# top of each other and hides all icons except the one identified by the
# fragment identifier in the embedding URL. We may get better performance in
# future by supporting a grid layout once Mozilla supports "zooming" to the
# identified icon.
#
# Alternatively this can be used to generate a file that just shows all the
# icons together (when referenced via a URI that doesn't contain a fragment
# identifier), if that's something someone wants.
#
USE_GRID_LAYOUT = False


import argparse, os, sys, re, math

epilog = """
This script comes from:

  https://github.com/gaia-components/gaia-icons/tree/master/

It is used to dump out a single "SVG icon set" file as source code containing
the source of all the SVG icon files in the 'images' directory. It cleans up
the source of the icons and adds an 'id' attribute to the root <svg> element of
each icon (the 'id' attribute being the name of the icon file without its
'.svg' suffix) before writing out the icon set file's contents. The resulting
SVG file provides a much more convenient way to move the icons around. More
importantly though, when the icons are referenced from a single SVG file then
browsers can provide better performance and use much less memory than if each
icon is in a separate SVG file. This is particularly important for Firefox OS
performance on lower end devices.

Example icon set file usage:

If you called the output file 'gaia-icons.svg', then to reference the
'back-arrow' icon from an <img> element you would use something like:

  <img src="gaia-icons.svg#back-arrow">

Any questions, ask Jonathan Watt <jwatt@jwatt.org>
"""

parser = argparse.ArgumentParser(description='Creates an SVG icon set file from multiple separate SVG icon files.',
                                 epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('-o', '--output', nargs=1, metavar="path", dest='iconset_path',
                    help='The path of the icon-set file to write the output to (stdout is used if this argument is not specified).')
parser.add_argument('iconsdir_path', metavar='icon-dir', nargs='?', default='./images',
                    help='The path to the directory containing the icon files ("./images" is assumed if this argument is not specified).')

args = parser.parse_args()

iconsdir_path = args.iconsdir_path
iconset_path = None
if args.iconset_path and len(args.iconset_path) > 0:
  iconset_path = args.iconset_path[0]

if not os.path.isdir(iconsdir_path):
  if (iconsdir_path == "./images"):
    sys.stderr.write('Error: The default icon files directory "./images" does not exist.\n')
    parser.print_usage(sys.stderr)
  else:
    sys.stderr.write('Error: Not a valid icon files directory: ' + iconsdir_path + '\n')
  sys.exit(1)

icons = filter(lambda n: n[-4:] == ".svg", os.listdir(iconsdir_path))

if len(icons) < 1:
  sys.stderr.write('Error: No .svg icon files found in directory: ' + iconsdir_path + '\n')
  sys.exit(1)

# cat * | sed 's/ xmlns:xlink="http:\/\/www.w3.org\/1999\/xlink"//' | sed 's/ xmlns="http:\/\/www.w3.org\/2000\/svg"//' | sed 's/ version="[^"]*"//' | sed '/<?xml /d' | sed '/<!-- Generated by/d' | sed '/<!DOCTYPE /d' | sed 's/><\/path>/\/>/' | sed '/<g>$/{N; /<g>\n<\/g>/d; }' | sed 's/ fill="#000000"//'

xmlns_re = re.compile(" xmlns=\"http://www.w3.org/2000/svg\"")
xlink_re = re.compile(" xmlns:xlink=\"http://www.w3.org/1999/xlink\"")
version_re = re.compile(" version=\"[^\"]+\"")
id_re = re.compile(" id=\"[^\"]+\"")
x_re = re.compile(" x=\"[^\"]+\"")
y_re = re.compile(" y=\"[^\"]+\"")
enable_background_re = re.compile(" enable-background=\"[^\"]+\"")
xml_space_re = re.compile(" xml:space=\"[^\"]+\"")
empty_g_re = re.compile("<g>\s+</g>\s*\n", re.M)
fill_re = re.compile(" fill=\"[^\"]+\"")
svg_open_tag_re = re.compile("^\s*<svg ")
svg_close_tag_re = re.compile("</svg>")
path_open_tag_re = re.compile("[ \t]*<path ")
path_close_tag_re = re.compile("></path>")

def clean_markup(markup, icon_name):
  # We drop the DOCTYPE, xml declaration, etc., since they are just bloat:
  start_index = markup.index("<svg ")
  end_of_start_tag_index = markup.index(">", start_index + 1) + 1
  start_tag = markup[start_index:end_of_start_tag_index]
  the_rest = markup[end_of_start_tag_index:]
  # get rid on the namespace declarations, since we'll have them on our root element:
  start_tag = xmlns_re.sub("", start_tag)
  start_tag = xlink_re.sub("", start_tag)
  # get rid of the 'id' attribute, since we're going to set a new one base on the file name:
  start_tag = id_re.sub("", start_tag)
  # get rid of the 'version' attribute, since it's unnecessary bloat:
  start_tag = version_re.sub("", start_tag)
  # get rid of the pointless 'x', 'y', 'enable-background' and 'xml:space' attributes if set:
  start_tag = x_re.sub("", start_tag)
  start_tag = y_re.sub("", start_tag)
  start_tag = enable_background_re.sub("", start_tag)
  start_tag = xml_space_re.sub("", start_tag)
  # set the 'id' attribute, and indent the start tag at the same time:
  start_tag = start_tag.replace("<svg", "  <svg id=\"" + icon_name + "\"")
  # get rid of the pointless empty <g> element:
  the_rest = empty_g_re.sub("", the_rest)
  # get rid of the 'fill' attribute, since we'll put one on the root element:
  the_rest = fill_re.sub("", the_rest)
  # use the short version of tag closing:
  the_rest = path_close_tag_re.sub("/>", the_rest)
  # clean up indentation (because we might as well):
  the_rest = svg_open_tag_re.sub("  <svg ", the_rest)
  the_rest = path_open_tag_re.sub("    <path ", the_rest)
  the_rest = svg_close_tag_re.sub("  </svg>", the_rest)
  if the_rest[0] != "\n": # the contents of some files are all on one line
    the_rest = "\n" + the_rest
  if the_rest[-1] != "\n": # the contents of some files are all on one line
    the_rest += "\n"
  return start_tag + the_rest

width_re = re.compile(" width=\"([^\"]+)\"")
height_re =  re.compile(" height=\"([^\"]+)\"")

def get_icon_dimensions_from_markup(markup):
  width = int(width_re.search(markup).group(1).replace("px", ""))
  height = int(height_re.search(markup).group(1).replace("px", ""))
  return [width, height]

icons_markup = []

for icon in icons:
  markup = open(os.path.join(iconsdir_path, icon)).read()
  markup = clean_markup(markup, icon.replace(".svg", ""))
  icons_markup.append(markup)

icons_dimensions = []

for markup in icons_markup:
  icons_dimensions.append(get_icon_dimensions_from_markup(markup))

[icon_width, icon_height] = icons_dimensions[0]
warn = False
for dim in icons_dimensions:
  [w, h] = dim
  if (w != icon_width):
    warn = True
    width = max(w, icon_width)
  if (h != icon_height):
    warn = True
    height = max(h, icon_height)
if warn:
  sys.stderr.write("\n<!-- !!! WARNING: NOT ALL ICON FILES HAVE THE SAME DIMENSIONS !!! -->\n\n")


output = "<!-- from https://github.com/gaia-components/gaia-icons/tree/master/images -->\n"

if not USE_GRID_LAYOUT:
  output += "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"" + str(icon_width) + "\" height=\"" + str(icon_height) + "\" fill=\"blue\">\n"
  output += "  <style>\n"
  output += "    :root > svg { visibility: hidden; }\n"
  output += "    :root > svg:target { visibility: visible; }\n"
  output += "  </style>\n"
  for markup in icons_markup:
    output += markup
  output += "</svg>\n"
else:
  # Else, we lay the icons out into a grid and require that the SVG implementation
  # properly implements http://www.w3.org/TR/SVG11/linking.html#SVGFragmentIdentifiers
  # Mozilla bug xxx-to-file needs fixed for this.
  cols = int(math.ceil(math.sqrt(len(icons))))
  rows = int(math.ceil(len(icons)/float(cols)))
  padding = 5 # the amount of room we give around each icon (in CSS px)
  
  total_width = str(icon_width * cols + padding * (cols+1))
  total_height = str(icon_height * rows + padding * (rows+1))
  
  # We do not set a width or height here, otherwise the fragment identifier linking can't work
  output += "<svg xmlns=\"http://www.w3.org/2000/svg\" fill=\"blue\">\n" # width=\"" + total_width + "\" height=\"" + total_height + "\"
  for i in range(len(icons)):
    row = i / cols
    col = i % cols
    x = padding + col * icon_width
    y = padding + row * icon_height
    markup = icons_markup[i]
    assert(markup[:6] == "  <svg")
    markup = markup[:6] + " x=\"" + str(x) + "\" y=\"" + str(y) + "\"" + markup[6:]
    output += markup
  output += "</svg>\n"

if iconset_path:
  iconset_file = open(iconset_path, "w")
  iconset_file.write(output)
  iconset_file.close()
else:
  sys.stdout.write(output)