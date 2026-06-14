import type { ReactNode } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { StatusBanner } from '@/components/common/StatusBanner'
import { StepFooter } from '@/components/common/StepFooter'

/**
 * Geçici adım iskeleti — tasarım kabuğunu (Step 1) göstermek için.
 * Her adım kendi görev dosyasında (Step 2–7) gerçek içerikle değiştirilecek.
 */
export function StepPlaceholder({
  title,
  description,
  implStep,
  children,
}: {
  title: string
  description: string
  implStep: string
  children?: ReactNode
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <StatusBanner tone="info">
          Bu ekran <strong>{implStep}</strong>'de uygulanacak. Şu an yalnızca tasarım kabuğu önizlemesi.
        </StatusBanner>
        {children}
        <StepFooter />
      </CardContent>
    </Card>
  )
}
