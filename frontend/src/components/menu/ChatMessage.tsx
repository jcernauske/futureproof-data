import { motion } from "framer-motion";
import { springs } from "@/styles/motion";
import type { ChatHistoryItem } from "@/api/menu";

interface ChatMessageProps {
  message: ChatHistoryItem;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const containerAlign = isUser ? "justify-end" : "justify-start";
  const bubble = isUser
    ? "bg-bp-surface rounded-tr-sm max-w-[80%]"
    : "bg-bp-deep rounded-tl-sm max-w-[90%]";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
      className={`flex w-full items-start gap-2 ${containerAlign}`}
      data-testid={`chat-message-${message.role}`}
    >
      {!isUser && (
        <span
          aria-hidden
          className="shrink-0 mt-2 w-6 h-6 rounded-full bg-accent-insight/15 text-accent-insight flex items-center justify-center text-micro"
        >
          ✦
        </span>
      )}
      <div
        className={`px-4 py-3 rounded-lg font-body text-body text-text-primary leading-relaxed ${bubble}`}
      >
        {message.content}
      </div>
    </motion.div>
  );
}
