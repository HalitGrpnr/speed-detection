import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, ClipboardList } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'

interface Props {
  jobId: string
}

const EVENT_LABELS: Record<string, string> = {
  pipeline_run: 'Analiz tamamlandı',
  axle_step_manual: 'Dingil adımlama (manuel)',
  axle_step_auto: 'Dingil adımlama (otomatik)',
  axle_check: 'Aks doğrulama',
  recalibrate_started: 'Yeniden kalibrasyon başlatıldı',
}

const EVENT_COLORS: Record<string, string> = {
  pipeline_run: 'bg-blue-100 text-blue-800',
  axle_step_manual: 'bg-purple-100 text-purple-800',
  axle_step_auto: 'bg-purple-100 text-purple-800',
  axle_check: 'bg-green-100 text-green-800',
  recalibrate_started: 'bg-amber-100 text-amber-800',
}

function LogEntry({ entry }: { entry: Record<string, unknown> }) {
  const [open, setOpen] = useState(false)
  const event = entry.event as string
  const ts = entry.ts as string
  const label = EVENT_LABELS[event] ?? event
  const colorClass = EVENT_COLORS[event] ?? 'bg-muted text-muted-foreground'

  const { ts: _ts, event: _ev, ...rest } = entry

  return (
    <div className="rounded border bg-card text-xs">
      <button
        className="flex w-full items-center gap-2 p-2 text-left"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? (
          <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" />
        )}
        <span className={`rounded px-1.5 py-0.5 font-medium ${colorClass}`}>{label}</span>
        <span className="ml-auto tabular-nums text-muted-foreground">{ts.replace('T', ' ')}</span>
      </button>

      {open && (
        <div className="border-t px-3 py-2">
          <table className="w-full text-xs">
            <tbody>
              {Object.entries(rest).map(([k, v]) => (
                <tr key={k} className="border-b last:border-0">
                  <td className="py-0.5 pr-3 font-mono text-muted-foreground w-40">{k}</td>
                  <td className="py-0.5 font-mono">
                    {typeof v === 'object' ? (
                      <pre className="whitespace-pre-wrap break-all text-[0.65rem]">
                        {JSON.stringify(v, null, 2)}
                      </pre>
                    ) : (
                      String(v)
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export function SessionLogPanel({ jobId }: Props) {
  const [visible, setVisible] = useState(false)

  const logQuery = useQuery({
    queryKey: ['sessionLog', jobId],
    queryFn: () => api.sessionLog(jobId),
    enabled: visible,
    staleTime: 30_000,
  })

  return (
    <div className="space-y-2">
      <Button
        variant="outline"
        size="sm"
        onClick={() => setVisible((v) => !v)}
        className="gap-2"
      >
        <ClipboardList className="size-3.5" />
        {visible ? 'Logu Gizle' : 'Test Logunu Göster'}
        {logQuery.data && (
          <span className="rounded-full bg-muted px-1.5 py-0.5 text-xs tabular-nums">
            {logQuery.data.length}
          </span>
        )}
      </Button>

      {visible && (
        <div className="space-y-1.5 rounded-lg border bg-muted/20 p-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span className="font-medium">Oturum Logu — Job: {jobId}</span>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={() => logQuery.refetch()}
            >
              Yenile
            </Button>
          </div>

          {logQuery.isLoading && (
            <p className="text-xs text-muted-foreground">Yükleniyor…</p>
          )}

          {logQuery.isError && (
            <p className="text-xs text-red-600">Log yüklenemedi.</p>
          )}

          {logQuery.data?.length === 0 && (
            <p className="text-xs text-muted-foreground">Henüz log kaydı yok.</p>
          )}

          {logQuery.data?.map((entry, i) => (
            <LogEntry key={i} entry={entry} />
          ))}
        </div>
      )}
    </div>
  )
}
