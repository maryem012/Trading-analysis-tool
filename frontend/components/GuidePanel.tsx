'use client'

export default function GuidePanel() {
  return (
    <details className="guide-panel card">
      <summary>📘 New to trading? Start here (2 min read)</summary>

      <div className="guide-body">
        <section>
          <h4>What this tool actually does</h4>
          <p>
            A <strong>strategy</strong> here is just a simple rule, like &ldquo;buy when the
            price crosses above its recent average, sell when it crosses back below.&rdquo;
            A <strong>backtest</strong> takes that rule and a stock&apos;s real price history,
            then replays it day by day, pretending to trade with <strong>a starting amount you
            choose — still entirely fake</strong>, to see what would have happened. It cannot
            predict the future — it only shows how a rule would have performed on the past.
          </p>
        </section>

        <section>
          <h4>How to read the four main numbers</h4>
          <ul className="guide-list">
            <li>
              <strong>Total Return</strong> — how much your fake starting amount grew or
              shrank, in percent. <span className="text-good">+10%</span> on $500 means it
              would be worth $550. Always compare this to &ldquo;Buy &amp; Hold&rdquo; (just
              buying the stock once and doing nothing) — beating that is the actual bar to
              clear, since anyone can do nothing.
            </li>
            <li>
              <strong>Win Rate</strong> — the percent of trades that made money. A 70% win
              rate sounds great, but on only 3 trades it&apos;s meaningless — you need dozens
              of trades before a win rate tells you much.
            </li>
            <li>
              <strong>Sharpe Ratio</strong> — return per unit of bumpiness. Roughly:
              above 1 is decent, above 2 is strong, below 0 means it lost money. Two strategies
              can make the same return, but the one with the higher Sharpe got there with a
              smoother ride.
            </li>
            <li>
              <strong>Max Drawdown</strong> — the worst dip from a peak, in percent. A
              -30% drawdown means at some point the fake account lost almost a third of its
              value before recovering. Ask yourself honestly: could you watch that happen to
              real money without panic-selling?
            </li>
          </ul>
        </section>

        <section>
          <h4>What BUY / SELL / HOLD mean on the Market &amp; Signals tab</h4>
          <p>
            These are what each rule would do <em>right now</em>, based on the same math as
            the backtest — not a prediction, not advice from a person, and not something acted
            on automatically. <strong>HOLD</strong> just means the rule&apos;s condition
            hasn&apos;t triggered; it&apos;s the most common state by far.
          </p>
        </section>

        <section>
          <h4>Planning to start small?</h4>
          <p>
            Set &ldquo;Starting Amount&rdquo; on the Backtest tab to whatever you&apos;d
            actually invest — $100, $500, whatever — so the dollar figures mean something to
            you, not an abstract $10,000. This tool assumes you can buy fractional shares (like
            0.2 of a share), which matches how most brokers actually work now (Robinhood,
            Fidelity, Schwab and others all offer fractional, commission-free trades), so an
            expensive stock or a small amount won&apos;t block a trade the way it would have a
            decade ago. Diversified funds (tickers like SPY or VTI — a single share holds
            hundreds of companies at once) are usually a gentler starting point than a single
            stock or crypto, since one company&apos;s bad week can&apos;t sink the whole thing.
          </p>
          <p className="guide-footer">
            Most major US brokers charge $0 commission on stock and ETF trades now, so that
            specific worry is smaller than it used to be — but this tool still doesn&apos;t
            model the bid-ask spread (the tiny gap between buy and sell price) or any fees at
            all, and a strategy that trades often will feel whatever does exist more, percentage-wise,
            on a smaller account. Crypto exchanges typically still charge real fees per trade,
            which is one more reason it&apos;s a rougher starting point than a stock or ETF.
          </p>
        </section>

        <section>
          <h4>Before you&apos;d trust a strategy, check these in order</h4>
          <ol className="guide-list">
            <li>Did it beat Buy &amp; Hold? If not, it added complexity for nothing.</li>
            <li>
              Does it have <strong>50+ closed trades</strong>? Fewer than that and the win rate
              is closer to a coin flip than a pattern — this app flags rows that clear this bar
              with a green <span className="pill win">✓</span>.
            </li>
            <li>Is expectancy (average return per trade) positive, not just the win rate?</li>
            <li>
              Could you stomach the Max Drawdown actually happening to money you care about?
            </li>
          </ol>
          <p className="guide-footer">
            If a strategy passes all four, that&apos;s a reason to keep testing it further —
            on a period it wasn&apos;t checked on, on other assets — not a reason to trade real
            money with it. This tool has no connection to any broker or exchange; it only ever
            reads public price history.
          </p>
        </section>
      </div>
    </details>
  )
}
