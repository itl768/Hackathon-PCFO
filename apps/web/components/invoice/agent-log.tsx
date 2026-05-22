"use client"

import { ChevronDown, ChevronUp, Terminal } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import type { AgentLogEntry } from "@/lib/invoice-types"

interface AgentLogProps {
  entries: AgentLogEntry[]
}

const AGENT_COLORS: Record<string, string> = {
  "Doc Reader": "text-sky-500",
  "DeDup File": "text-violet-500",
  Extractor: "text-blue-500",
  "DeDup MCP": "text-purple-500",
  Embeddings: "text-cyan-500",
  Validator: "text-emerald-500",
  "Anomaly Detector": "text-amber-500",
  Responder: "text-rose-500",
}

const STATUS_DOT: Record<string, string> = {
  success: "bg-emerald-500",
  warning: "bg-amber-500",
  error: "bg-red-500",
  info: "bg-blue-500",
}

export function AgentLog({ entries }: AgentLogProps) {
  const [collapsed, setCollapsed] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current && !collapsed) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [entries, collapsed])

  return (
    <div className="border-t bg-card">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex w-full items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
      >
        <Terminal className="h-3.5 w-3.5" />
        Agent Communication Log
        <span className="ml-1 rounded-full bg-muted px-1.5 py-0.5 text-[10px]">
          {entries.length}
        </span>
        <div className="flex-1" />
        {collapsed ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
      </button>

      {!collapsed && (
        <div ref={scrollRef} className="max-h-40 overflow-y-auto px-4 pb-3">
          {entries.length === 0 ? (
            <p className="py-2 text-xs text-muted-foreground">
              Waiting for pipeline to start...
            </p>
          ) : (
            <div className="flex flex-col gap-0.5">
              {entries.map((entry, i) => (
                <div key={i} className="flex items-start gap-2 py-0.5">
                  <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
                    {entry.timestamp}
                  </span>
                  <span
                    className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${STATUS_DOT[entry.status] || STATUS_DOT.info}`}
                  />
                  <span
                    className={`shrink-0 text-[11px] font-bold ${AGENT_COLORS[entry.agent_name] || "text-foreground"}`}
                  >
                    {entry.agent_name}:
                  </span>
                  <span className="text-[11px] text-foreground/80">{entry.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
