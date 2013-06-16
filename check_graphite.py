#!/usr/bin/python

"""
MIT License Boilerplate
Copyright (C) 2013 Joel Krauska

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


Summary:
This script is meant to be run as a nagios plugin to poll graphite for data and trigger nagios alerts.

Requirements:
  requests, nagaconda and pickle

Example usage: (checking diamond's cpu stat for user cpu percentage)
(Diamond is an awesome stats collector for graphite -- https://github.com/BrightcoveOS/Diamond)

./check_graphite.py -h graphite.example.com -t "diamond.testhost.cpu.total.user" -w 50 -c 80
checking warning
range was warning
(0, 50.0, False)
51.03:0:50.0 =  True
checking critical
range was critical
(0, 80.0, False)
51.03:0:80.0 =  False
Status Warning, diamondervers.testhost.cpu.total.user = 51.030000|diamond.testhost.cpu.total.user=51.03;50;80;;
"""

import sys
import pickle

try:
    import requests
except ImportError:
    print("ERROR: Unable to import requests -- required for simplified http interaction.\nTry: pip install requests")
    sys.exit(2)

try:
    from NagAconda import Plugin
except ImportError:
    print("ERROR: Unable to import NagAconda -- required for simplified Nagios interaction.\nTry: pip install nagaconda")
    sys.exit(2)

debug=False

# Poll stats from graphite and normalize
def get_value(url):
    r = requests.get(url)
    if r.status_code == 200:
        try: 
            data = pickle.loads(r.content)[0]
        except: 
            # corrupt/empty return data
            return (None)

        if 'values' in data:
            # Replace Nones with 0
            # Fixme: better to remove None values?
            vals = [x if x != None else 0 for x in data['values']]
            if debug: print 'DEBUG VALUES:',vals
            # return an average
            return (float(sum(vals))/float(len(vals)))
        else:
            return (None)
    else:
        # non 200 return code
        return (None)

g = Plugin("Graphite Nagios Plugin.", "0.9")

# FIXME: http vs https support, user auth?
g.add_option('t', 'target', 'Graphite Target', required=True)
g.add_option('h', 'host',   'Graphite Host', required=True)
g.add_option('w', 'window', 'Time Window', default='-5minutes')
g.add_option('u', 'units',  'Metric units', default='percent')

g.enable_status('critical')
g.enable_status('warning')

g.start()

# Bounds checking on crit and warn
if g.options.raw_critical < g.options.raw_warning:
    g.unknown_error("ERROR: Critical level (%s) is set LOWER than Warning level (%s)" % (
        g.options.raw_critical,
        g.options.raw_warning,
        ))

# Build url
# FIXME: pickle seems efficient, but maybe harder to debug?
url = 'http://%s/render?from=%s&target=%s&format=pickle' % (
    g.options.host, 
    g.options.window,
    g.options.target,
    )
if debug: print 'DEBUG URL:',url

value=get_value(url)
if debug: print 'DEBUG VALUE:', value

# Error parsing
if value == None:
    g.unknown_error("ERROR: Could not parse data from URL - %s" % url)

# Set it and forget it
g.set_value(g.options.target, float(value))
g.set_status_message("%s = %f" % (g.options.target, value))

g.finish()
