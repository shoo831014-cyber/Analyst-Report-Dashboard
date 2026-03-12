(() => {
  const root = document.documentElement;
  const body = document.body;
  const themeToggleButton = document.querySelector("[data-theme-toggle-button]");
  const chips = document.querySelectorAll(".date-chip");
  const themeStorageKey = "dashboardTheme";

  function getPreferredTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(theme) {
    root.dataset.theme = theme;
    if (!themeToggleButton) {
      return;
    }

    const isDark = theme === "dark";
    themeToggleButton.textContent = isDark
      ? (themeToggleButton.dataset.darkLabel || "라이트 모드")
      : (themeToggleButton.dataset.lightLabel || "다크 모드");
    themeToggleButton.setAttribute("aria-pressed", isDark ? "true" : "false");
  }

  applyTheme(root.dataset.theme || getPreferredTheme());

  if (themeToggleButton) {
    themeToggleButton.addEventListener("click", () => {
      const nextTheme = root.dataset.theme === "dark" ? "light" : "dark";
      applyTheme(nextTheme);
      try {
        window.localStorage.setItem(themeStorageKey, nextTheme);
      } catch (error) {
        console.error(error);
      }
    });
  }

  for (const chip of chips) {
    chip.addEventListener("click", () => {
      body.classList.add("is-loading");
    });
  }

  const updateButton = document.querySelector("[data-manual-update-button]");
  const updateStatus = document.querySelector("[data-manual-update-status]");
  const lastUpdatedText = document.querySelector("[data-last-updated-text]");

  if (!updateButton) {
    return;
  }

  const defaultButtonLabel = updateButton.dataset.defaultLabel || updateButton.textContent.trim();

  function setUpdatingState(isUpdating, statusText, statusTone = "idle") {
    updateButton.disabled = isUpdating;
    updateButton.textContent = isUpdating ? "업데이트 진행 중..." : defaultButtonLabel;
    updateButton.classList.toggle("is-loading", isUpdating);
    body.classList.toggle("is-loading", isUpdating);
    body.classList.toggle("is-updating", isUpdating);

    if (updateStatus) {
      updateStatus.textContent = statusText;
      updateStatus.dataset.tone = statusTone;
      updateStatus.classList.toggle("is-loading", isUpdating);
    }
  }

  updateButton.addEventListener("click", async () => {
    if (updateButton.disabled) {
      return;
    }

    setUpdatingState(true, "업데이트 진행 중입니다. 완료까지 잠시 기다려 주세요.", "loading");

    try {
      const response = await fetch("/api/v1/dashboard/update", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const payload = await response.json();
      const snapshotDate = payload.snapshot_date;
      const updatedAtText = payload.last_updated_text || "-";

      if (updateStatus) {
        updateStatus.textContent = `${snapshotDate} 업데이트 완료`;
        updateStatus.dataset.tone = "success";
        updateStatus.classList.remove("is-loading");
      }

      if (lastUpdatedText) {
        lastUpdatedText.textContent = `마지막 업데이트 ${updatedAtText}`;
      }

      updateButton.textContent = "업데이트 완료";
      body.classList.remove("is-loading");
      body.classList.remove("is-updating");

      window.setTimeout(() => {
        window.location.href = `/dashboard?date=${encodeURIComponent(snapshotDate)}`;
      }, 900);
    } catch (error) {
      console.error(error);
      setUpdatingState(false, "업데이트 실패", "error");
      window.alert("수동 업데이트 중 오류가 발생했습니다.");
    }
  });
})();
