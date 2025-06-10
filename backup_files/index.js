import { useState, useEffect } from "react";
import axios from "axios";
import Sidebar from "@/components/Sidebar";
import HeaderBar from "@/components/HeaderBar";
import InputZone from "@/components/InputZone";
import LoaderAnimation from "@/components/LoaderAnimation";
import WelcomeScreen from "@/components/WelcomeScreen";
import { AnimatePresence, motion } from "framer-motion";
import ChatView from "@/components/ChatView";
import { v4 as uuidv4 } from "uuid";

export default function Home() {
  // Text & DOST state
  const [queryText, setQueryText] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionUUID, setSessionUUID] = useState(null);
  const [responseReady, setResponseReady] = useState(false);
  const [loaderFastMode, setLoaderFastMode] = useState(false);
  const [pendingMessage, setPendingMessage] = useState(null);

  // Welcome screen
  const [showWelcomeScreen, setShowWelcomeScreen] = useState(true);

  // Voice recording state
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);

  // Layout state
  const [collapsed, setCollapsed] = useState(false);

  // Conversation messages
  const [messages, setMessages] = useState([]);

  // Image & caption state
  const [rawImage, setRawImage] = useState(null);
  const [imageContext, setImageContext] = useState("");

  // Cancellation / pause
  const [cancelSource, setCancelSource] = useState(null);

  // Generate session UUID on component mount
  useEffect(() => {
    setSessionUUID(uuidv4());
  }, []);

  // Preset handler
  const handlePresetClick = (preset) => {
    setQueryText(preset);
    setTimeout(() => handleTextSubmit(preset), 100);
  };

  // Build pendingMessage for DOST/general blocks
  const buildPendingMessage = (response) => {
    const generalScript = response.data.reasoning?.general_script || [];
    const resultData = response.data.result?.data || {};
    const allResults = Object.values(resultData).flat();
    const uniqueResults = allResults.filter((item, idx, arr) => {
      const linkKey = Object.keys(item).find((k) => k.toLowerCase().includes("link"));
      const url = item[linkKey] || "";
      return arr.findIndex((i) => (i[linkKey] || "") === url) === idx;
    });
    const isGeneralQuery = Object.keys(resultData).length === 0;
    if (isGeneralQuery) {
      return { id: uuidv4(), type: "general-query", script: generalScript, needsTyping: true };
    }
    if (generalScript.length && uniqueResults.length) {
      return {
        id: uuidv4(),
        type: "mixed-combo",
        general_script: generalScript,
        main_script: "",
        results: uniqueResults,
        needsTyping: true,
      };
    }
    return { id: uuidv4(), type: "dost-combo", text: "", results: uniqueResults, needsTyping: true };
  };

  // Pause/cancel handler (works for text, image, AND voice)
  const handleCancelRequest = () => {
    if (cancelSource) {
      cancelSource.cancel("User paused the request");
      setLoading(false);
      setPendingMessage(null);
      setCancelSource(null);
    }
  };

  // Main DOST request handler (text or image+caption)
  const handleTextSubmit = async (customQuery = null) => {
    const userText = customQuery !== null
      ? customQuery
      : rawImage
        ? imageContext
        : queryText;
    if (!rawImage && !userText.trim()) return;

    // Prepare cancel token
    const source = axios.CancelToken.source();
    setCancelSource(source);

    // Prepare user message
    const baseContext = rawImage ? imageContext.trim() : "";
    const previewUrl = rawImage ? URL.createObjectURL(rawImage) : null;
    let displayText;
    if (rawImage) displayText = baseContext
      ? `<b>Context:</b> ${baseContext}\nProcessing your image…`
      : "Processing your image…";
    else displayText = userText;
    const userMsgId = uuidv4();
    setMessages((prev) => [...prev, { id: userMsgId, type: "user", text: displayText, imagePreview: previewUrl, needsTyping: true }]);

    // Clear inputs
    setQueryText("");
    setRawImage(null);
    setImageContext("");

    setLoading(true);
    setResponseReady(false);
    setLoaderFastMode(false);
    setShowWelcomeScreen(false);

    try {
      const formData = new FormData();
      if (rawImage) {
        formData.append("image", rawImage, "upload.png");
        formData.append("context", userText);
      } else {
        formData.append("query", userText);
      }
      const response = await axios.post(
        "https://acadza-params-api.onrender.com/process-query",
        formData,
        { cancelToken: source.token, headers: { "Content-Type": "multipart/form-data", authorization: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY1ZmMxMTg1MTBhMjJjMjAwOTEzNDk4OSIsInJvbGUiOiJ0ZWFjaGVyIiwiaWF0IjoxNzQ0OTQ4OTk0LCJleHAiOjE3NDY2NzY5OTR9.e0LyfLeaMYWOFv4HTRDbP61zwA9U2n79yL-I7XkH_yw", "student-id": "65fc118510a22c2009134989", "Session-UUID": sessionUUID } }
      );
      console.log("🛠 DOST API response:", response.data);
      if (previewUrl && response.data.query) {
        const prefix = baseContext ? `<b>Context:</b> ${baseContext}\n` : "";
      
        // 1) Ensure we have an object, not a raw string
        let parsed;
        if (typeof response.data.query === "string") {
          try {
            parsed = JSON.parse(response.data.query);
          } catch {
            parsed = { text: response.data.query };
          }
        } else {
          parsed = response.data.query;
        }
      
        // 2) Pick .text first, then .latex, else fall back
        let content;
        if (parsed.text) {
          content = parsed.text;
        } else if (parsed.latex) {
          // wrap in display-math delimiters for parseRichText
          content = `\\[${parsed.latex.trim()}\\]`;
        } else {
          content = JSON.stringify(parsed);
        }
      
        // 3) Update only the inner text
        setMessages(prev =>
          prev.map(m =>
            m.id === userMsgId
              ? { ...m, text: `${prefix}${content}` }
              : m
          )
        );
      }
      const pendingMsg = buildPendingMessage(response);
      setPendingMessage(pendingMsg);
      setResponseReady(true);
      setLoaderFastMode(true);
    } catch (err) {
      if (!axios.isCancel(err)) {
        console.error("Error in process-query:", err);
        alert("Something went wrong!");
      }
      setLoading(false);
    } finally {
      setCancelSource(null);
    }
  };

  // Voice recording handler
  const handleMicClick = async () => {
    if (isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
      setCancelSource(null);
      return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    setMediaRecorder(recorder);
    const audioChunks = [];
    recorder.ondataavailable = (e) => audioChunks.push(e.data);
    
    recorder.onstop = async () => {
      const tempId = uuidv4();
      setMessages((prev) => [...prev, { id: tempId, type: "user", text: "Processing your voice...", needsTyping: true }]);
      const previewUrl = rawImage ? URL.createObjectURL(rawImage) : null;
      if (rawImage) {
        setMessages((prev) => prev.map(m => m.id === tempId ? { ...m, text: imageContext ? `<b>Context:</b> ${imageContext}\nProcessing your voice...` : "Processing your voice...", imagePreview: previewUrl } : m));
      }

      setRawImage(null);
      setImageContext("");
      setLoading(true);
      setResponseReady(false);
      setLoaderFastMode(false);
      setShowWelcomeScreen(false);

      // Prepare cancel token for voice
      const source = axios.CancelToken.source();
      setCancelSource(source);

      try {
        const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
        const formData = new FormData();
        let combinedContext = imageContext.trim();
        formData.append("file", audioBlob, "query.wav");
        if (rawImage) {
          formData.append("image", rawImage, "upload.png");
          if (combinedContext) {
            formData.append("context", combinedContext);
          }
        }
        const response = await axios.post(
          "https://acadza-params-api.onrender.com/process-query",
          formData,
          { cancelToken: source.token, headers: { "Content-Type": "multipart/form-data", authorization: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY1ZmMxMTg1MTBhMjJjMjAwOTEzNDk4OSIsInJvbGUiOiJ0ZWFjaGVyIiwiaWF0IjoxNzQ0OTQ4OTk0LCJleHAiOjE3NDY2NzY5OTR9.e0LyfLeaMYWOFv4HTRDbP61zwA9U2n79yL-I7XkH_yw", "student-id": "65fc118510a22c2009134989", "Session-UUID": sessionUUID } }
        );
        const transcribed = response.data.query?.text || response.data.query || "Voice input";
        console.log("🛠 Voice API response:", response.data);
        setMessages((prev) => [
          ...prev.filter((m) => m.id !== tempId),
          { id: uuidv4(), type: "user", text: rawImage ? (imageContext ? `<b>Context:</b> ${imageContext}\n${transcribed}` : transcribed) : transcribed, imagePreview: previewUrl, needsTyping: true },
        ]);
    
        const pendingMsg = buildPendingMessage(response);
        setPendingMessage(pendingMsg);
        setResponseReady(true);
        setLoaderFastMode(true);
      } catch (err) {
        if (axios.isCancel(err)) {
          console.log("Voice request canceled by user");
        } else {
          console.error("Error in voice process-query:", err);
          alert("Something went wrong!");
        }
        setLoading(false);
      } finally {
        setCancelSource(null);
      }
    };
    recorder.start();
    setIsRecording(true);
  };

  return (
    <div className="flex min-h-screen bg-white">
      {/* Sidebar is completely hidden on <md */}
      <div className="hidden md:flex">
        <Sidebar collapsed={collapsed} toggleSidebar={() => setCollapsed(!collapsed)} />
      </div>
      {/* Main content: no margin on mobile, but shift on md+ */}
      <div className={`flex-1 flex flex-col transition-all duration-300 ml-0 ${collapsed ? "md:ml-20" : "md:ml-64"}`}>
        <HeaderBar collapsed={collapsed} />
        <main className="pt-16 px-0 md:px-6 pb-24 flex-grow overflow-y-auto">
          <AnimatePresence mode="wait">
            {showWelcomeScreen ? (
              <motion.div key="welcome" initial={{ opacity: 0, y: 50 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -50 }} transition={{ duration: 0.5 }} className="flex flex-col items-center">
                <WelcomeScreen onPresetClick={handlePresetClick} />
              </motion.div>
            ) : (
              <motion.div key="maincontent" initial={{ opacity: 0, y: 50 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -50 }} transition={{ duration: 0.5 }} className="flex flex-col">
                <ChatView
                  messages={messages}
                  loading={loading}
                  responseReady={responseReady}
                  loaderFastMode={loaderFastMode}
                  pendingMessage={pendingMessage}
                  setPendingMessage={setPendingMessage}
                  setMessages={setMessages}
                  onLoaderFinish={() => setLoading(false)}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </main>
        <InputZone
          queryText={queryText}
          setQueryText={setQueryText}
          rawImage={rawImage}
          setRawImage={setRawImage}
          imageContext={imageContext}
          setImageContext={setImageContext}
          isLoading={loading}
          isPaused={!!cancelSource}
          onPauseClick={handleCancelRequest}
          handleTextSubmit={handleTextSubmit}
          handleMicClick={handleMicClick}
          isRecording={isRecording}
          collapsed={collapsed}
        />
      </div>
    </div>
  );
}