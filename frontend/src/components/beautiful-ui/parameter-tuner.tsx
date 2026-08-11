import { Input } from '@/components/ui/control'

export type ParameterDefinition = {
  id: string
  label: string
  max: number
  min: number
  step?: number
  value: number
}

export type ParameterTunerProps = {
  label: string
  onChange(id: string, value: number): void
  parameters: readonly ParameterDefinition[]
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

export function ParameterTuner({ label, onChange, parameters }: ParameterTunerProps) {
  return (
    <section aria-label={label} className="grid gap-3" data-slot="parameter-tuner">
      <h2 className="text-sm font-medium">{label}</h2>
      <div className="grid gap-3">
        {parameters.map((parameter) => (
          <div className="grid gap-1" key={parameter.id}>
            <label className="text-sm font-medium" htmlFor={`parameter-${parameter.id}`}>
              {parameter.label}
            </label>
            <Input
              id={`parameter-${parameter.id}`}
              max={parameter.max}
              min={parameter.min}
              onChange={(event) => {
                const value = event.target.valueAsNumber
                if (!Number.isNaN(value)) onChange(parameter.id, clamp(value, parameter.min, parameter.max))
              }}
              step={parameter.step ?? 1}
              type="number"
              value={parameter.value}
            />
          </div>
        ))}
      </div>
    </section>
  )
}
