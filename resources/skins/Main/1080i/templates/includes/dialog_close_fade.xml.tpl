{# The pop-ups' fade out: a window animation, so the frame, its dim and any panel beside it go together. Without it
   a pop-up closed over a still screen stayed on the AM6B (CoreELEC p3i) until something else on the screen changed:
   Kodi redraws once as a dialog closes, and there that one frame never reached the screen. A fade is several frames,
   as Kodi's own dialogs close. In 0.3.0 the user menu and the sidebar's menus were in-screen dropdowns, and the
   screen changed as they closed. #}
<animation effect="fade" start="100" end="0" time="100">WindowClose</animation>
