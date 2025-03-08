
import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, Command } from "lucide-react";
import { cn } from "@/lib/utils";

interface TextInputProps {
  onSendMessage: (message: string) => void;
  className?: string;
  placeholder?: string;
}

// Define available commands
const COMMANDS = [
  {
    command: "/newAgent",
    description: "Create a new pizza agent",
  },
  {
    command: "/help",
    description: "Show available commands",
  },
  {
    command: "/menu",
    description: "Show the pizza menu",
  },
];

const TextInput: React.FC<TextInputProps> = ({
  onSendMessage,
  className,
  placeholder = "Type your message...",
}) => {
  const [message, setMessage] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<typeof COMMANDS>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // Filter suggestions based on input
  useEffect(() => {
    if (message.startsWith("/")) {
      const filteredSuggestions = COMMANDS.filter((cmd) =>
        cmd.command.toLowerCase().includes(message.toLowerCase())
      );
      setSuggestions(filteredSuggestions);
      setShowSuggestions(filteredSuggestions.length > 0);
    } else {
      setShowSuggestions(false);
    }
  }, [message]);

  // Handle clicking outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim()) {
      onSendMessage(message);
      setMessage("");
      setShowSuggestions(false);
    }
  };

  const handleSuggestionClick = (command: string) => {
    setMessage(command + " ");
    setShowSuggestions(false);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  return (
    <div className="relative w-full max-w-md">
      <form
        onSubmit={handleSubmit}
        className={cn(
          "flex w-full items-center space-x-2 rounded-full border border-orange-200 bg-amber-50 p-1 shadow-sm transition-all focus-within:ring-1 focus-within:ring-amber-400",
          className
        )}
      >
        <div className="relative flex-1">
          <Input
            ref={inputRef}
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={placeholder}
            className="flex-1 border-0 bg-transparent focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-transparent text-stone-800 pl-3"
          />
          {message.startsWith("/") && (
            <div className="absolute left-2 top-1/2 -translate-y-1/2 pointer-events-none opacity-40">
              <Command className="h-4 w-4" />
            </div>
          )}
        </div>
        <Button
          type="submit"
          size="icon"
          variant="ghost"
          className="h-8 w-8 rounded-full bg-red-600 text-white hover:bg-red-700"
          disabled={!message.trim()}
        >
          <Send className="h-4 w-4" />
          <span className="sr-only">Send</span>
        </Button>
      </form>

      {/* Command suggestions dropdown */}
      {showSuggestions && (
        <div
          ref={suggestionsRef}
          className="absolute mt-1 w-full max-h-48 overflow-y-auto bg-amber-50 rounded-md shadow-md border border-orange-200 z-10"
        >
          {suggestions.map((suggestion) => (
            <div
              key={suggestion.command}
              className="px-3 py-2 hover:bg-amber-100 cursor-pointer flex items-center gap-2"
              onClick={() => handleSuggestionClick(suggestion.command)}
            >
              <Command className="h-4 w-4 text-stone-500" />
              <div>
                <div className="font-medium text-stone-800">{suggestion.command}</div>
                <div className="text-xs text-stone-500">{suggestion.description}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TextInput;
