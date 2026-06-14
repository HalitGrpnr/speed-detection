import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { StatusBanner } from '@/components/common/StatusBanner'
import { useWizard } from '@/store/wizard'

export function ResultsStep() {
  const reset = useWizard((s) => s.reset)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Adım 6 — Sonuçlar</CardTitle>
        <CardDescription>
          Hız tablosu (güven aralığı + güven seviyesiyle), overlay video ve PDF rapor burada gösterilir.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <StatusBanner tone="info">
          Bu ekran <strong>Step 7</strong>'de uygulanacak. Şu an yalnızca tasarım kabuğu önizlemesi.
        </StatusBanner>
        <Button variant="secondary" onClick={reset}>
          Yeni Analiz
        </Button>
      </CardContent>
    </Card>
  )
}
