import { useId } from 'react'

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
  const instanceId = useId()

  return (
    <div aria-label={label} className="grid gap-3" data-slot="parameter-tuner" role="group">
      <h2 className="text-sm font-medium">{label}</h2>
      <div className="grid gap-3">
        {parameters.map((parameter) => {
          const inputId = `parameter-${instanceId}-${parameter.id}`
          return (
            <div className="grid gap-1" key={parameter.id}>
              <label className="text-sm font-medium" htmlFor={inputId}>
                {parameter.label}
              </label>
              <Input
                id={inputId}
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
          )
        })}
      </div>
    </div>
  )
}
