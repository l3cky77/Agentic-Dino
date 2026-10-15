(() => {
  const messages = document.getElementById("messages");
  const welcome = document.getElementById("welcomeBlock");
  const input = document.getElementById("messageInput");
  const send = document.getElementById("sendButton");
  const toast = document.getElementById("toast");
  const historyPanel = document.getElementById("historyPanel");
  let history = [];
  let busy = false;
  let toastTimer;

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 3000);
  }
  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
  }
  function formatText(text) {
    // Escape first; add only basic inline formatting, never render model HTML.
    return escapeHtml(text)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br>");
  }
  function addMessage(role, content) {
    welcome.classList.add("is-hidden");
    const row = document.createElement("div");
    row.className = `message-row ${role}`;
    const avatar = role === "assistant" ? '<div class="message-avatar">D</div>' : '<div class="message-avatar user-msg-avatar">YOU</div>';
    row.innerHTML = `${avatar}<div class="message-content"><div class="message-author">${role === "assistant" ? "Dino AI" : "You"}<span>${role === "assistant" ? "AI ASSISTANT" : "YOUR MESSAGE"}</span></div><div class="message-text">${formatText(content)}</div></div>`;
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
    return row;
  }
  function setBusy(value) {
    busy = value;
    send.disabled = value;
    send.innerHTML = value ? '<span class="send-spinner"></span>' : "↑";
    input.disabled = value;
  }
  async function sendMessage(text) {
    text = (text || input.value).trim();
    if (!text || busy) return;
    history.push({role: "user", content: text});
    addMessage("user", text);
    input.value = "";
    input.style.height = "auto";
    setBusy(true);
    const waiting = addMessage("assistant", "Thinking through that…");
    waiting.classList.add("is-thinking");
    try {
      const response = await fetch("/api/chat", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({message: text, history: history.slice(-8)})
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Request failed");
      waiting.remove();
      addMessage("assistant", data.reply || "I didn't receive a response.");
      history.push({role: "assistant", content: data.reply || ""});
      loadTasks();
    } catch (error) {
      waiting.remove();
      addMessage("assistant", `I couldn't complete that request. ${error.message} Please try again.`);
      showToast(error.message);
    } finally {
      setBusy(false);
      input.focus();
    }
  }
  send.addEventListener("click", () => sendMessage());
  input.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 150) + "px";
  });
  document.querySelectorAll("[data-prompt]").forEach(button => {
    button.addEventListener("click", () => sendMessage(button.dataset.prompt));
  });
  document.getElementById("newChat").addEventListener("click", () => {
    history = [];
    messages.innerHTML = "";
    welcome.classList.remove("is-hidden");
    input.value = "";
    input.focus();
  });
  document.getElementById("showHistory").addEventListener("click", () => historyPanel.classList.add("open"));
  document.getElementById("closeHistory").addEventListener("click", () => historyPanel.classList.remove("open"));
  document.getElementById("mobileMenu").addEventListener("click", () => document.getElementById("sidebar").classList.toggle("mobile-open"));

  async function loadTasks() {
    const list = document.getElementById("taskList");
    try {
      const response = await fetch("/api/tasks");
      if (!response.ok) return;
      const data = await response.json();
      if (!data.tasks.length) {
        list.innerHTML = '<div class="empty-state">Your recent prompts will appear here.</div>';
        return;
      }
      list.innerHTML = data.tasks.map(task => `
        <button class="task-item" data-task-id="${task.id}">
          <span class="task-status">✓</span>
          <span class="task-item-copy"><b>${escapeHtml(task.prompt)}</b><small>${new Date(task.created_at + "Z").toLocaleString()} · ${escapeHtml(task.status)}</small></span>
        </button>`).join("");
      list.querySelectorAll(".task-item").forEach((button, i) => {
        button.addEventListener("click", () => {
          const task = data.tasks[i];
          historyPanel.classList.remove("open");
          addMessage("user", task.prompt);
          addMessage("assistant", task.result || "No saved result for this task.");
        });
      });
    } catch (_) {}
  }
  loadTasks();
})();
