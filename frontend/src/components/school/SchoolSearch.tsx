import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { apiGet } from "@/api/client";
import type { SchoolSearchResult, SchoolSelection } from "@/types/buildInput";

interface SchoolSearchProps {
  onSelect: (school: SchoolSelection) => void;
  selected: SchoolSelection | null;
  onClear: () => void;
}

export function SchoolSearch({
  onSelect,
  selected,
  onClear,
}: SchoolSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SchoolSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const dropdownRef = useRef<HTMLUListElement>(null);

  const search = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([]);
      setShowDropdown(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<SchoolSearchResult[]>(
        `/schools/?q=${encodeURIComponent(q)}`,
      );
      setResults(data);
      setShowDropdown(data.length > 0);
      if (data.length === 0) {
        setError("No schools found. Try a different name or abbreviation.");
      }
    } catch {
      setError("Having trouble searching. Try again in a moment.");
      setResults([]);
      setShowDropdown(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    setQuery(val);
    setHighlightIndex(-1);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(val), 300);
  }

  function handleSelect(result: SchoolSearchResult) {
    onSelect({
      unitid: result.unitid,
      name: result.institution_name,
      institutionControl: result.institution_control,
      netPriceAnnual: result.net_price_annual,
      costOfAttendanceAnnual: result.cost_of_attendance_annual,
    });
    setShowDropdown(false);
    setQuery("");
    setResults([]);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!showDropdown) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && highlightIndex >= 0 && results[highlightIndex]) {
      e.preventDefault();
      handleSelect(results[highlightIndex]);
    } else if (e.key === "Escape") {
      setShowDropdown(false);
    }
  }

  useEffect(() => {
    if (highlightIndex >= 0 && dropdownRef.current) {
      const item = dropdownRef.current.children[highlightIndex] as HTMLElement;
      item?.scrollIntoView({ block: "nearest" });
    }
  }, [highlightIndex]);

  if (selected) {
    return (
      <motion.div
        className="flex items-center gap-2 bg-bp-deep rounded-lg h-14 px-4 border border-border"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={springs.smooth}
      >
        <span className="text-text-primary font-semibold flex-1 truncate">
          {selected.name}
        </span>
        <button
          onClick={onClear}
          className="text-text-muted hover:text-text-secondary transition-colors duration-fast cursor-pointer shrink-0 p-1"
          aria-label="Clear school selection"
        >
          ✕
        </button>
      </motion.div>
    );
  }

  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={() => results.length > 0 && setShowDropdown(true)}
        placeholder="Search for your school..."
        className={`w-full bg-bp-deep text-text-primary font-body text-body px-4 py-3 h-14 rounded-lg border border-border focus:border-accent-info focus:shadow-[0_0_0_3px_var(--color-focus-ring)] focus:outline-none transition-colors duration-normal placeholder:text-text-muted ${
          loading ? "animate-pulse border-accent-info/50" : ""
        }`}
        aria-label="Search for your school"
        aria-expanded={showDropdown}
        aria-controls="school-results"
        role="combobox"
        aria-autocomplete="list"
        aria-activedescendant={
          highlightIndex >= 0 ? `school-result-${highlightIndex}` : undefined
        }
      />

      <AnimatePresence>
        {showDropdown && (
          <motion.ul
            ref={dropdownRef}
            id="school-results"
            role="listbox"
            className="absolute z-50 w-full mt-1 bg-bp-mid border border-border rounded-lg shadow-lg max-h-[320px] overflow-y-auto overflow-hidden"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
          >
            {results.map((result, i) => (
              <li
                key={result.unitid}
                id={`school-result-${i}`}
                role="option"
                aria-selected={i === highlightIndex}
                className={`flex justify-between items-center px-[18px] py-3 cursor-pointer transition-[background] duration-fast border-b border-border-subtle last:border-b-0 ${
                  i === highlightIndex
                    ? "bg-[rgba(125,212,163,0.1)] border-l-[3px] border-l-accent-thrive"
                    : "hover:bg-bp-surface"
                }`}
                onClick={() => handleSelect(result)}
                onMouseEnter={() => setHighlightIndex(i)}
              >
                <span className="font-semibold" style={{ fontSize: 15 }}>
                  {result.institution_name}
                </span>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>

      {error && !showDropdown && (
        <motion.p
          className="mt-2 text-sm text-text-muted"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {error}
        </motion.p>
      )}
    </div>
  );
}
