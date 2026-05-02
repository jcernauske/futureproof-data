import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { springs } from "@/styles/motion";
import type { ChatHistoryItem } from "@/api/menu";

interface ChatMessageProps {
  message: ChatHistoryItem;
}

/**
 * Markdown rendering is opt-in for ASSISTANT messages only — user
 * messages render as plain text since they're the student's own
 * input. Gemma's answers (especially multi-tool ones) tend to use
 * `**bold**` headings + bulleted lists; rendering them as markdown
 * makes those structured answers actually scannable.
 *
 * Component allowlist: paragraphs, strong, em, ordered/unordered
 * lists, list items, links (open in new tab), inline code. We
 * deliberately drop headings and code fences — Gemma's chat answers
 * shouldn't ever need them and they'd compete visually with the
 * trace's own headers.
 */
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
        {isUser ? (
          message.content
        ) : (
          <ReactMarkdown
            components={{
              // Paragraphs — keep tight spacing inside the bubble.
              p: ({ children }) => (
                <p className="m-0 [&:not(:first-child)]:mt-3">{children}</p>
              ),
              // Bold — Gemma's structural cues; tint to text-primary.
              strong: ({ children }) => (
                <strong className="font-semibold text-text-primary">
                  {children}
                </strong>
              ),
              em: ({ children }) => <em className="italic">{children}</em>,
              // Lists — small left indent, comfortable line gap.
              ul: ({ children }) => (
                <ul className="list-disc pl-5 mt-2 space-y-1">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal pl-5 mt-2 space-y-1">{children}</ol>
              ),
              li: ({ children }) => <li className="leading-relaxed">{children}</li>,
              // Inline code — match the engineering view's data font.
              code: ({ children }) => (
                <code className="font-data text-data-sm bg-bp-mid px-1 py-0.5 rounded-sm">
                  {children}
                </code>
              ),
              // Links — accent-info, open in new tab, safe rel.
              a: ({ href, children }) => (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent-info underline underline-offset-2 hover:text-text-primary"
                >
                  {children}
                </a>
              ),
              // Headings collapse to bold spans — Gemma chat answers
              // don't need a hierarchy and headings would fight the
              // <GemmaTrace> header above.
              h1: ({ children }) => (
                <p className="m-0 mt-3 font-semibold text-text-primary">
                  {children}
                </p>
              ),
              h2: ({ children }) => (
                <p className="m-0 mt-3 font-semibold text-text-primary">
                  {children}
                </p>
              ),
              h3: ({ children }) => (
                <p className="m-0 mt-3 font-semibold text-text-primary">
                  {children}
                </p>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </motion.div>
  );
}
