(() => {
  const pairForm = document.getElementById("pairForm");
  const pairCode = document.getElementById("pairCode");
  const pairStatus = document.getElementById("pairStatus");
  const urlForm = document.getElementById("urlForm");
  const targetUrl = document.getElementById("targetUrl");
  const urlStatus = document.getElementById("urlStatus");
  const openUrl = document.getElementById("openUrl");
  let validatedUrl = "";

  pairForm.addEventListener("submit", async event => {
    event.preventDefault();
    pairStatus.className = "inline-status";
    pairStatus.textContent = "Checking code…";
    try {
      const response = await fetch("/api/pair", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({code: pairCode.value.replace(/\s/g, "")})
      });
      const data = await response.json();
      pairStatus.textContent = data.message || data.error;
      pairStatus.classList.add(response.ok ? "success" : "error");
    } catch (_) {
      pairStatus.textContent = "Could not reach Dino AI. Try again.";
      pairStatus.classList.add("error");
    }
  });

  urlForm.addEventListener("submit", async event => {
    event.preventDefault();
    openUrl.classList.add("hidden");
    urlStatus.className = "inline-status";
    urlStatus.textContent = "Validating URL…";
    try {
      const response = await fetch("/api/open-url", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({url: targetUrl.value})
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "URL validation failed");
      validatedUrl = data.url;
      urlStatus.textContent = "URL looks valid. You can open it in this browser after confirming.";
      urlStatus.classList.add("success");
      openUrl.classList.remove("hidden");
    } catch (error) {
      urlStatus.textContent = error.message;
      urlStatus.classList.add("error");
    }
  });
  openUrl.addEventListener("click", () => {
    if (!validatedUrl || !confirm(`Open this website in a new tab?\n\n${validatedUrl}`)) return;
    window.open(validatedUrl, "_blank", "noopener,noreferrer");
  });
})();
