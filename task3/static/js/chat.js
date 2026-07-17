(() => {
  "use strict";

  const SESSION_STORAGE_KEY = "safebank_session_id";

  function getSessionId() {
    let sessionId = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!sessionId) {
      sessionId = crypto.randomUUID();
      sessionStorage.setItem(SESSION_STORAGE_KEY, sessionId);
    }
    return sessionId;
  }

  const chatWindow = document.getElementById("chat-window");
  const chatForm = document.getElementById("chat-form");
  const messageInput = document.getElementById("message-input");
  const sendButton = document.getElementById("send-button");
  const loadingIndicator = document.getElementById("loading-indicator");
  const errorBanner = document.getElementById("error-banner");
  const fraudBanner = document.getElementById("fraud-banner");
  const riskCard = document.getElementById("risk-card");
  const riskLevelValue = document.getElementById("risk-level-value");
  const riskConfidenceValue = document.getElementById("risk-confidence-value");
  const riskFlagsList = document.getElementById("risk-flags-list");
  const suggestedActionsCard = document.getElementById("suggested-actions-card");
  const suggestedActionsList = document.getElementById("suggested-actions-list");

  function appendMessage(role, text) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${role}`;
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    wrapper.appendChild(bubble);
    chatWindow.appendChild(wrapper);
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  function clearList(listElement) {
    while (listElement.firstChild) {
      listElement.removeChild(listElement.firstChild);
    }
  }

  function renderList(listElement, items) {
    clearList(listElement);
    for (const item of items) {
      const li = document.createElement("li");
      li.textContent = item;
      listElement.appendChild(li);
    }
  }

  function showRiskAssessment(assessment) {
    if (!assessment) {
      riskCard.classList.add("hidden");
      return;
    }
    riskCard.classList.remove("hidden");
    riskLevelValue.textContent = assessment.risk_level.toUpperCase();
    riskLevelValue.className = `risk-level-badge risk-level-${assessment.risk_level}`;
    riskConfidenceValue.textContent = `${Math.round(assessment.confidence * 100)}%`;
    renderList(riskFlagsList, assessment.flags.length ? assessment.flags : ["None detected"]);
  }

  function showSuggestedActions(actions) {
    if (!actions || actions.length === 0) {
      suggestedActionsCard.classList.add("hidden");
      return;
    }
    suggestedActionsCard.classList.remove("hidden");
    renderList(suggestedActionsList, actions);
  }

  function showFraudBanner(assessment, escalation) {
    if (!assessment || assessment.risk_level !== "high") {
      fraudBanner.classList.add("hidden");
      fraudBanner.textContent = "";
      return;
    }
    let text = "⚠️ High fraud risk detected. Do not click links or share codes.";
    if (escalation) {
      text += ` This case has been escalated for review (ticket ${escalation.ticket_id}).`;
    }
    fraudBanner.textContent = text;
    fraudBanner.classList.remove("hidden");
  }

  function showError(message) {
    errorBanner.textContent = message;
    errorBanner.classList.remove("hidden");
  }

  function clearError() {
    errorBanner.textContent = "";
    errorBanner.classList.add("hidden");
  }

  function setLoading(isLoading) {
    loadingIndicator.classList.toggle("hidden", !isLoading);
    sendButton.disabled = isLoading;
  }

  async function sendMessage(message) {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: getSessionId(), message }),
    });

    let data = null;
    try {
      data = await response.json();
    } catch (parseError) {
      throw new Error("The server returned an unreadable response. Please try again.");
    }

    if (!response.ok) {
      throw new Error(data && data.detail ? data.detail : "Something went wrong. Please try again.");
    }
    return data;
  }

  chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = messageInput.value.trim();
    if (!message) {
      return;
    }

    clearError();
    appendMessage("user", message);
    messageInput.value = "";
    setLoading(true);

    try {
      const data = await sendMessage(message);
      appendMessage("assistant", data.reply);
      showRiskAssessment(data.fraud_assessment);
      showSuggestedActions(data.suggested_actions);
      showFraudBanner(data.fraud_assessment, data.escalation);
    } catch (error) {
      showError(error.message || "Network error. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  });
})();
