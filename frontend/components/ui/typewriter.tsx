"use client";

import { useEffect, useMemo, useState } from "react";

interface TypewriterProps {
  words: string[];
  speed?: number;
  delayBetweenWords?: number;
  cursor?: boolean;
  cursorChar?: string;
}

export function Typewriter({
  words,
  speed = 100,
  delayBetweenWords = 2000,
  cursor = true,
  cursorChar = "|",
}: TypewriterProps) {
  const safeWords = useMemo(() => words.filter(Boolean), [words]);
  const [displayText, setDisplayText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [wordIndex, setWordIndex] = useState(0);
  const [charIndex, setCharIndex] = useState(0);
  const [showCursor, setShowCursor] = useState(true);

  const currentWord = safeWords[wordIndex] ?? "";

  useEffect(() => {
    if (!currentWord) {
      setDisplayText("");
      return undefined;
    }

    const isComplete = !isDeleting && charIndex === currentWord.length;
    const isDeleted = isDeleting && charIndex === 0;
    const timeoutDelay = isComplete ? delayBetweenWords : isDeleting ? speed / 2 : speed;

    const timeout = window.setTimeout(() => {
      if (isComplete) {
        setIsDeleting(true);
        return;
      }

      if (isDeleted) {
        setIsDeleting(false);
        setWordIndex((prev) => (prev + 1) % safeWords.length);
        return;
      }

      const nextCharIndex = isDeleting ? charIndex - 1 : charIndex + 1;
      setDisplayText(currentWord.substring(0, nextCharIndex));
      setCharIndex(nextCharIndex);
    }, timeoutDelay);

    return () => window.clearTimeout(timeout);
  }, [charIndex, currentWord, delayBetweenWords, isDeleting, safeWords.length, speed]);

  useEffect(() => {
    if (!cursor) return undefined;

    const cursorInterval = window.setInterval(() => {
      setShowCursor((prev) => !prev);
    }, 500);

    return () => window.clearInterval(cursorInterval);
  }, [cursor]);

  return (
    <span className="typewriter">
      <span>
        {displayText}
        {cursor ? (
          <span className="typewriter-cursor" style={{ opacity: showCursor ? 1 : 0 }} aria-hidden="true">
            {cursorChar}
          </span>
        ) : null}
      </span>
    </span>
  );
}
