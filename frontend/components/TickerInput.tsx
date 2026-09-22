'use client'

interface TickerInputProps {
  id: string
  value: string
  onChange: (v: string) => void
  suggestions: string[]
}

/**
 * Free-text ticker entry with autocomplete suggestions — not a restriction.
 * Every backend endpoint accepts any ticker yfinance recognizes (any stock,
 * ETF, index prefixed "^", or crypto pair like "ETH-USD"); `suggestions` is
 * just a starting list, not a whitelist.
 */
export default function TickerInput({ id, value, onChange, suggestions }: TickerInputProps) {
  const listId = `${id}-suggestions`
  return (
    <>
      <input
        id={id}
        type="text"
        list={listId}
        value={value}
        onChange={(e) => onChange(e.target.value.toUpperCase())}
        placeholder="AAPL, TSLA, ETH-USD..."
        spellCheck={false}
        autoComplete="off"
      />
      <datalist id={listId}>
        {suggestions.map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>
    </>
  )
}
