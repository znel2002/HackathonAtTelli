import React, { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Mic, Keyboard, Volume2, VolumeX, Pizza } from "lucide-react";
import { cn } from "@/lib/utils";
import VoiceCircle from "./VoiceCircle";
import TextInput from "./TextInput";
import { useToast } from "@/components/ui/use-toast";

type VoiceStatus = "idle" | "speaking" | "listening";

interface Message {
  id: string;
  text: string;
  sender: "user" | "agent";
  timestamp: Date;
}

interface VoiceAgentProps {
  className?: string;
}

// Declare SpeechRecognition types
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

const VoiceAgent: React.FC<VoiceAgentProps> = ({ className }) => {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [isTextMode, setIsTextMode] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome-message",
      text: "Hello, I'm your assistant! 🍕 How can I help with your today?",
      sender: "agent",
      timestamp: new Date(),
    },
  ]);
  const [hasStarted, setHasStarted] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const { toast } = useToast();

  // Helper to convert a base64 string to a Blob
  const base64ToBlob = (base64: string, contentType: string) => {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: contentType });
  };

  // Establish the WebSocket connection when the component mounts
  useEffect(() => {
    const socket = new WebSocket(`ws://localhost:8000/ws`);
    setWs(socket);

    socket.onopen = () => {
      console.log("WebSocket connection opened");
    };

    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "ack") {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              text: msg.data,
              sender: "agent",
              timestamp: new Date(),
            },
          ]);
          setHasStarted(true);
        } else if (msg.type === "question" || msg.type === "feedback") {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              text: msg.data,
              sender: "agent",
              timestamp: new Date(),
            },
          ]);
        } else if (msg.type === "feedback_audio") {
          setStatus("speaking");
          const audioBlob = base64ToBlob(msg.data, "audio/mpeg");
          const audioUrl = URL.createObjectURL(audioBlob);
          const audioElement = new Audio(audioUrl);
          if (!isMuted) {
            audioElement.play().then(() => {});
          }
          audioElement.onended = () => {
            setStatus("idle");
            URL.revokeObjectURL(audioUrl);
          };
        } else if (msg.type === "finished") {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              text: msg.data,
              sender: "agent",
              timestamp: new Date(),
            },
          ]);
          setStatus("idle");
        }
      } catch (error) {
        console.error("Error parsing message", error);
      }
    };

    socket.onclose = () => {
      console.log("WebSocket connection closed");
      setWs(null);
    };

    return () => {
      socket.close();
    };
  }, [isMuted]);

  // Command execution: /newagent, /help, /menu
  const executeCommand = useCallback(
    (command: string) => {
      const commandName = command.split(" ")[0].toLowerCase().trim();
      if (commandName === "/newagent") {
        // Extract the task text from the command (everything after "/newagent")
        const taskText = command.substring("/newagent".length).trim();
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "newAgent", data: taskText }));
          toast({
            title: "New Agent Created",
            description: "Starting new agent with task: " + taskText,
          });
        }
        return true;
      }
      if (commandName === "/help") {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            text: "Available commands:\n• /newagent [task] - Create a new pizza agent with the specified task\n• /help - Show this help message\n• /menu - Show our pizza menu",
            sender: "agent",
            timestamp: new Date(),
          },
        ]);
        return true;
      }
      if (commandName === "/menu") {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            text: "🍕 Our Pizza Menu 🍕\n• Margherita - $12\n• Pepperoni - $14\n• Veggie Supreme - $15\n• Meat Lovers - $16\n• Hawaiian - $13\n• PizzaBot Special - $18",
            sender: "agent",
            timestamp: new Date(),
          },
        ]);
        return true;
      }
      return false;
    },
    [ws, toast]
  );

  // Handle sending a message via WebSocket only.
  const handleSendMessage = useCallback(
    async (text: string) => {
      const userMessage: Message = {
        id: Date.now().toString(),
        text,
        sender: "user",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Execute as command if starts with "/"
      if (text.startsWith("/")) {
        const executed = executeCommand(text);
        if (executed) return;
      }

      if (ws && ws.readyState === WebSocket.OPEN) {
        const messageType = hasStarted ? "text" : "start";
        ws.send(JSON.stringify({ type: messageType, data: text }));
        if (!hasStarted) setHasStarted(true);
      } else {
        toast({
          title: "WebSocket Error",
          description: "The connection is not open. Please try again later.",
          variant: "destructive",
        });
      }
    },
    [executeCommand, hasStarted, ws, toast]
  );

  // Handle voice input using SpeechRecognition API
  const handleVoiceInput = useCallback(() => {
    if (
      !("webkitSpeechRecognition" in window) &&
      !("SpeechRecognition" in window)
    ) {
      toast({
        title: "Speech Recognition Not Supported",
        description:
          "Your browser doesn't support speech recognition. Try using a modern browser or switch to text input.",
        variant: "destructive",
      });
      return;
    }
    setStatus("listening");
    const SpeechRecognitionAPI =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognitionAPI();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const speechResult = event.results[0][0].transcript;
      handleSendMessage(speechResult);
    };
    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      console.error("Speech recognition error", event.error);
      setStatus("idle");
      toast({
        title: "Voice Recognition Error",
        description: `Error: ${event.error}. Please try again or switch to text input.`,
        variant: "destructive",
      });
    };
    recognition.onend = () => {
      setStatus("idle");
    };
    recognition.start();
  }, [handleSendMessage, toast]);

  // Toggle mute state
  const toggleMute = useCallback(() => {
    setIsMuted((prev) => !prev);
    toast({
      title: isMuted ? "Sound Enabled" : "Sound Muted",
      description: isMuted
        ? "You will now hear responses."
        : "You will no longer hear responses.",
    });
  }, [isMuted, toast]);

  // Toggle input mode
  const toggleInputMode = useCallback(() => {
    setIsTextMode((prev) => !prev);
  }, []);

  return (
    <div className={cn("flex flex-col items-center", className)}>
      <div className="mb-4">
        <Pizza className="h-12 w-12 text-red-500" />
      </div>
      <div className="w-full max-w-lg h-[300px] mb-8 overflow-y-auto rounded-lg bg-orange-50/80 backdrop-blur-sm p-4 border border-orange-200 shadow-sm">
        {messages.map((message) => (
          <div
            key={message.id}
            className={cn(
              "mb-4 p-3 rounded-lg max-w-[80%]",
              message.sender === "user"
                ? "ml-auto bg-red-600 text-white"
                : "mr-auto bg-amber-100 text-stone-800 border border-orange-200"
            )}
          >
            <p className="whitespace-pre-line">{message.text}</p>
            <span className="text-xs opacity-70 mt-1 block">
              {message.timestamp.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
        ))}
      </div>
      <VoiceCircle status={status} size="lg" className="mb-8" />
      <div className="flex flex-col items-center space-y-4">
        {isTextMode ? (
          <TextInput
            onSendMessage={handleSendMessage}
            className="mb-4"
            placeholder="Order your pizza here..."
          />
        ) : (
          <Button
            onClick={handleVoiceInput}
            disabled={status !== "idle"}
            size="lg"
            variant="outline"
            className={cn(
              "h-12 w-12 rounded-full transition-all",
              status === "idle"
                ? "bg-amber-50 hover:bg-amber-100 border-orange-200"
                : "bg-amber-100 border-orange-300"
            )}
          >
            <Mic
              className={cn(
                "h-6 w-6",
                status !== "idle" ? "text-red-600" : "text-stone-700"
              )}
            />
            <span className="sr-only">Speak</span>
          </Button>
        )}
        <div className="flex items-center space-x-2">
          <Button
            onClick={toggleInputMode}
            variant="outline"
            size="icon"
            className="rounded-full bg-amber-50 hover:bg-amber-100 border-orange-200"
          >
            {isTextMode ? (
              <Mic className="h-4 w-4 text-stone-700" />
            ) : (
              <Keyboard className="h-4 w-4 text-stone-700" />
            )}
            <span className="sr-only">
              {isTextMode ? "Switch to voice input" : "Switch to text input"}
            </span>
          </Button>
          <Button
            onClick={toggleMute}
            variant="outline"
            size="icon"
            className="rounded-full bg-amber-50 hover:bg-amber-100 border-orange-200"
          >
            {isMuted ? (
              <VolumeX className="h-4 w-4 text-stone-700" />
            ) : (
              <Volume2 className="h-4 w-4 text-stone-700" />
            )}
            <span className="sr-only">{isMuted ? "Unmute" : "Mute"}</span>
          </Button>
        </div>
      </div>
    </div>
  );
};

export default VoiceAgent;
