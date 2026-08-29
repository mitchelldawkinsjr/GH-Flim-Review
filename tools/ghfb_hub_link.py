"""Shared back link to Godwin Heights team tools hub."""

HUB_HOME_ABSOLUTE = "https://ghfb.360web.cloud/index.html"

HUB_LINK_CSS = """
.hub-back { margin: 0 0 16px; font-size: 14px; }
.hub-back a { color: #e5a32a; text-decoration: none; font-weight: 600; }
.hub-back a:hover { text-decoration: underline; }
"""

HUB_LINK_HTML = (
    f'<p class="hub-back"><a href="{HUB_HOME_ABSOLUTE}" data-ghfb-hub-link>← Team Tools</a></p>'
)

HUB_LINK_SCRIPT = """
<script>
(function () {
  var a = document.querySelector("[data-ghfb-hub-link]");
  if (!a) return;
  var h = location.hostname;
  if (h === "ghfb.360web.cloud" || h === "localhost" || h === "127.0.0.1") {
    a.href = "/index.html";
  }
})();
</script>
"""
