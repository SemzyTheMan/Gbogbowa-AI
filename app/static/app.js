const $ = (id) => document.getElementById(id);
const phone = $("phone");
let busy = false,
  recorder = null,
  stream = null,
  clip = null,
  clipUrl = null,
  ticker = null,
  started = 0,
  requestingMic = false;
try {
  phone.value = localStorage.getItem("gbogbowa-phone") || "";
} catch {}
function status(message, error = false) {
  $("status").textContent = message;
  $("status").classList.toggle("error", error);
}
function validPhone() {
  const value = phone.value.trim();
  if (!/^\+?[0-9]{7,15}$/.test(value)) {
    status(
      "Enter your business phone number, including country code, to continue.",
      true,
    );
    phone.focus();
    return null;
  }
  try {
    localStorage.setItem("gbogbowa-phone", value);
  } catch {}
  return value;
}
function lock(value) {
  busy = value;
  for (const id of [
    "send",
    "record",
    "send-voice",
    "discard",
    "phone",
    "message",
  ])
    $(id).disabled = value;
}
function bubble(text, who) {
  $("welcome")?.remove();
  const element = document.createElement("div");
  element.className = `bubble ${who}`;
  const label = document.createElement("small");
  label.textContent = who === "user" ? "YOU" : "GBOGBOWA";
  element.append(label, document.createTextNode(text));
  $("conversation").append(element);
  $("conversation").scrollTop = $("conversation").scrollHeight;
  return element;
}
async function request(url, options, responseField = "reply") {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 180000);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error(
        "The server returned an unreadable response. Please try again.",
      );
    }
    if (!response.ok) {
      if (response.status === 404 && url === "/ai/voice")
        throw new Error(
          "Let’s set up your account first. Type a greeting below and follow the assistant’s instructions.",
        );
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : "We couldn’t complete that instruction. Please check your details and try again.",
      );
    }
    if (typeof data[responseField] !== "string")
      throw new Error("The assistant returned an unexpected response.");
    return data;
  } catch (error) {
    if (error.name === "AbortError")
      throw new Error(
        "The request timed out. Check your conversation before repeating a sale or stock update.",
      );
    if (error instanceof TypeError)
      throw new Error(
        "Connection lost. Check your connection and verify your records before repeating an update.",
      );
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}
$("message-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy || recorder?.state === "recording" || requestingMic) return;
  const number = validPhone(),
    text = $("message").value.trim();
  if (!number) return;
  if (!text) {
    status("Type an instruction, or tap the microphone.", true);
    $("message").focus();
    return;
  }
  lock(true);
  status("Working on your instruction…");
  bubble(text, "user");
  try {
    const data = await request("/ai/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone_number: number,
        text,
        message_id: crypto.randomUUID(),
      }),
    });
    bubble(data.reply, "assistant");
    $("message").value = "";
    status("Reply received.");
  } catch (error) {
    status(error.message, true);
  } finally {
    lock(false);
  }
});
phone.addEventListener("change", () => {
  // Keep conversations from different business numbers visually separate.
  document.querySelectorAll(".bubble").forEach((element) => element.remove());
  discard();
  status("Business number updated.");
});
function releaseMic() {
  stream?.getTracks().forEach((track) => track.stop());
  stream = null;
  clearInterval(ticker);
  document.body.classList.remove("recording");
  $("timer").hidden = true;
}
function discard() {
  clip = null;
  if (clipUrl) URL.revokeObjectURL(clipUrl);
  clipUrl = null;
  $("preview").removeAttribute("src");
  $("preview").load();
  $("recording-review").hidden = true;
  $("voice-title").textContent = "Tap to speak";
  $("voice-help").textContent = "Up to 2 minutes";
}
$("discard").addEventListener("click", () => {
  discard();
  status("Recording discarded.");
});
$("record").addEventListener("click", async () => {
  // Recording locks the other controls, but the mic must remain a stop button.
  if (recorder?.state === "recording") {
    recorder.stop();
    return;
  }
  if (busy || requestingMic) return;
  if (!validPhone()) return;
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    status(
      "Recording is unavailable here. Open this page over HTTPS or localhost in a supported browser, or type your instruction.",
      true,
    );
    return;
  }
  requestingMic = true;
  lock(true);
  status("Allow microphone access to record.");
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    discard();
    const mimeType = [
      "audio/webm;codecs=opus",
      "audio/mp4",
      "audio/ogg;codecs=opus",
    ].find((type) => MediaRecorder.isTypeSupported(type));
    recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
    const chunks = [];
    let failed = false;
    recorder.ondataavailable = (event) => {
      if (event.data.size) chunks.push(event.data);
    };
    recorder.onerror = () => {
      failed = true;
      releaseMic();
      lock(false);
      status("Recording failed. Please try again.", true);
    };
    recorder.onstop = () => {
      releaseMic();
      lock(false);
      $("record").setAttribute("aria-label", "Start recording");
      if (failed) return;
      clip = new Blob(chunks, { type: recorder.mimeType });
      if (!clip.size || Date.now() - started < 600) {
        discard();
        status(
          "Recording was too short. Please speak for at least one second.",
          true,
        );
        return;
      }
      clipUrl = URL.createObjectURL(clip);
      $("preview").src = clipUrl;
      $("recording-review").hidden = false;
      $("voice-title").textContent = "Review your recording";
      $("voice-help").textContent = "Listen, then check the transcript.";
      status("");
    };
    recorder.start();
    started = Date.now();
    document.body.classList.add("recording");
    $("record").disabled = false;
    $("record").setAttribute("aria-label", "Stop recording");
    $("voice-title").textContent = "Tap to stop";
    $("voice-help").textContent = "Tap again to stop. Maximum 2 minutes.";
    $("timer").hidden = false;
    $("timer").textContent = "00:00 / 02:00";
    status("");
    ticker = setInterval(() => {
      const seconds = Math.floor((Date.now() - started) / 1000);
      $("timer").textContent =
        `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")} / 02:00`;
      if (seconds >= 119 && recorder.state === "recording") recorder.stop();
    }, 250);
  } catch (error) {
    releaseMic();
    lock(false);
    status(
      error.name === "NotAllowedError"
        ? "Microphone access was blocked. Allow it in your browser settings, or type below."
        : "Couldn’t open your microphone. Check that it’s connected and try again.",
      true,
    );
  } finally {
    requestingMic = false;
  }
});
$("send-voice").addEventListener("click", async () => {
  if (busy || !clip) return;
  const number = validPhone();
  if (!number) return;
  if ($("message").value.trim()) {
    status("Send or clear your typed instruction before transcribing a voice note.", true);
    $("message").focus();
    return;
  }
  lock(true);
  status("Transcribing…");
  const data = new FormData();
  data.append("phone_number", number);
  data.append("transcribe_only", "true");
  const extension = clip.type.includes("mp4")
    ? "m4a"
    : clip.type.includes("ogg")
      ? "ogg"
      : "webm";
  data.append("audio", clip, `voice.${extension}`);
  try {
    const result = await request("/ai/voice", { method: "POST", body: data }, "transcript");
    $("message").value = result.transcript;
    discard();
    status("Check the prices, edit if needed, then Send. Nothing has been saved yet.");
  } catch (error) {
    status(error.message, true);
  } finally {
    lock(false);
    $("message").focus();
  }
});
window.addEventListener("pagehide", () => {
  if (recorder?.state === "recording") recorder.stop();
  releaseMic();
  if (clipUrl) URL.revokeObjectURL(clipUrl);
});
