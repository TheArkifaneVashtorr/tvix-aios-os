_: {
  # Hardened Firefox via declarative enterprise policies. Policy reference:
  # https://mozilla.github.io/policy-templates/ — values here are locked from
  # about:config where the policy engine supports it.
  programs.firefox = {
    enable = true;
    policies = {
      DisableTelemetry = true;
      DisableFirefoxStudies = true;
      DisablePocket = true;
      DisableFeedbackCommands = true;
      DontCheckDefaultBrowser = true;
      # Proton Pass owns credentials; the built-in manager stays off.
      PasswordManagerEnabled = false;
      OfferToSaveLogins = false;
      EnableTrackingProtection = {
        Value = true;
        Locked = true;
        Cryptomining = true;
        Fingerprinting = true;
      };
      HttpsOnlyMode = "enabled";
      ExtensionSettings = {
        # uBlock Origin, force-installed and unremovable.
        "uBlock0@raymondhill.net" = {
          installation_mode = "force_installed";
          install_url = "https://addons.mozilla.org/firefox/downloads/latest/ublock-origin/latest.xpi";
        };
      };
      Preferences = {
        "browser.contentblocking.category" = {
          Value = "strict";
          Status = "locked";
        };
        "browser.newtabpage.activity-stream.showSponsored" = {
          Value = false;
          Status = "locked";
        };
        "browser.newtabpage.activity-stream.showSponsoredTopSites" = {
          Value = false;
          Status = "locked";
        };
        "network.prefetch-next" = {
          Value = false;
          Status = "locked";
        };
        "network.dns.disablePrefetch" = {
          Value = true;
          Status = "locked";
        };
        "network.http.speculative-parallel-limit" = {
          Value = 0;
          Status = "locked";
        };
        # Firefox already exempts loopback from HTTPS-Only upgrades by
        # default; this pins that default explicitly so Helm's plain-http
        # http://localhost:7700 dashboard keeps loading under
        # HttpsOnlyMode = "enabled" above (docs/superpowers/specs/
        # 2026-09-02-helm-design.md).
        "dom.security.https_only_mode.upgrade_local" = false;
      };
    };
  };
}
