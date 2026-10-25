#!/bin/bash
export DISPLAY=:99
CH=/nix/store/jaf9gnbln0cbs2vspfdblc4ff6vv1kk5-chromium-142.0.7444.175/bin/chromium
exec $CH --no-sandbox --disable-dev-shm-usage --remote-debugging-port=9333 \
  --remote-allow-origins=* \
  --window-size=800,500 --window-position=0,0 --disable-gpu --disable-software-rasterizer \
  --autoplay-policy=no-user-gesture-required \
  "file:///data/workspace/luoshen-o1/感官桥/片.html"
