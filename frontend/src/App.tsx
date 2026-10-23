import React, { useState } from 'react';
import {
  SAMPLE_VALID_SMALL,
  SAMPLE_VALID_AUTO,
  SAMPLE_VALID_LARGE,
  SAMPLE_SEMANTIC_CAPACITY_ERROR,
  SAMPLE_SEMANTIC_CONFLICT_ERROR,
  SAMPLE_SYNTAX_ERROR,
  SAMPLE_LEXICAL_ERROR,
} from './examples';
import { compileSource } from './api';
import type { CompileResponse } from './types';

export const App: React.FC = () => {
  const [source, setSource] = useState<string>(SAMPLE_VALID_SMALL);
  const [maxSlots, setMaxSlots] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [response, setResponse] = useState<CompileResponse | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'timetable' | 'ast' | 'symbols' | 'ir' | 'tokens' | 'help'>('timetable');

  const handleCompile = async () => {
    setLoading(true);
    setClientError(null);
    try {
      const parsedSlots = maxSlots.trim() ? parseInt(maxSlots.trim(), 10) : null;
      const res = await compileSource(source, parsedSlots);
      setResponse(res);
      if (!res.success) {
        // Automatically switch to help or timetable/overview
        if (res.stage_failed === 'parser') setActiveTab('ast');
        else if (res.stage_failed === 'semantic') setActiveTab('symbols');
        else if (res.stage_failed === 'lexer') setActiveTab('tokens');
      } else {
        setActiveTab('timetable');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setClientError(msg);
      setResponse(null);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadExample = (exampleCode: string) => {
    setSource(exampleCode);
    setResponse(null);
    setClientError(null);
  };

  const handleClear = () => {
    setSource('');
    setResponse(null);
    setClientError(null);
  };

  // Pipeline step badge helper
  const getStepStatus = (stageName: 'lexer' | 'parser' | 'ast' | 'semantic' | 'ir' | 'generator' | 'verifier') => {
    if (loading) return 'step-running';
    if (!response) return '';
    const st = response.stages[stageName];
    if (!st) return '';
    if (st.status === 'passed') return 'step-passed';
    if (st.status === 'failed') return 'step-failed';
    return '';
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand-section">
          <h1>TimetableLang</h1>
          <p>A Domain-Specific Language for Examination Timetable Validation and Generation</p>
        </div>
        <div>
          {loading ? (
            <span className="header-status-badge badge-running">● Compiling...</span>
          ) : clientError ? (
            <span className="header-status-badge badge-failed">● API Disconnected</span>
          ) : response ? (
            response.success ? (
              <span className="header-status-badge badge-passed">✓ Verification Passed</span>
            ) : (
              <span className="header-status-badge badge-failed">✕ Compilation Failed</span>
            )
          ) : (
            <span className="header-status-badge badge-idle">● Ready to compile</span>
          )}
        </div>
      </header>

      {/* Compiler Pipeline Visualization */}
      <section className="pipeline-section">
        <div className="pipeline-steps">
          <div className={`pipeline-step ${getStepStatus('lexer')}`}>
            <span>1. Lexer</span>
          </div>
          <span className="pipeline-arrow">→</span>
          <div className={`pipeline-step ${getStepStatus('parser')}`}>
            <span>2. Parser</span>
          </div>
          <span className="pipeline-arrow">→</span>
          <div className={`pipeline-step ${getStepStatus('ast')}`}>
            <span>3. AST</span>
          </div>
          <span className="pipeline-arrow">→</span>
          <div className={`pipeline-step ${getStepStatus('semantic')}`}>
            <span>4. Semantic Analysis</span>
          </div>
          <span className="pipeline-arrow">→</span>
          <div className={`pipeline-step ${getStepStatus('ir')}`}>
            <span>5. Intermediate Code</span>
          </div>
          <span className="pipeline-arrow">→</span>
          <div className={`pipeline-step ${getStepStatus('generator')}`}>
            <span>6. Generator</span>
          </div>
          <span className="pipeline-arrow">→</span>
          <div className={`pipeline-step ${getStepStatus('verifier')}`}>
            <span>7. Verifier</span>
          </div>
        </div>
      </section>

      {/* Main Workspace */}
      <main className="main-workspace">
        {/* Source Code Editor Panel */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Source Editor (.tt)</span>
            <div className="toolbar-group">
              <button
                className="btn-secondary"
                onClick={() => handleLoadExample(SAMPLE_VALID_SMALL)}
              >
                Valid (Fixed)
              </button>
              <button
                className="btn-secondary"
                onClick={() => handleLoadExample(SAMPLE_VALID_AUTO)}
              >
                Valid (AUTO)
              </button>
              <button
                className="btn-secondary"
                onClick={() => handleLoadExample(SAMPLE_VALID_LARGE)}
              >
                Valid (Large)
              </button>
              <button
                className="btn-secondary"
                onClick={() => handleLoadExample(SAMPLE_SEMANTIC_CAPACITY_ERROR)}
              >
                Capacity Error
              </button>
              <button
                className="btn-secondary"
                onClick={() => handleLoadExample(SAMPLE_SEMANTIC_CONFLICT_ERROR)}
              >
                Conflict Error
              </button>
              <button
                className="btn-secondary"
                onClick={() => handleLoadExample(SAMPLE_SYNTAX_ERROR)}
              >
                Syntax Error
              </button>
              <button
                className="btn-secondary"
                onClick={() => handleLoadExample(SAMPLE_LEXICAL_ERROR)}
              >
                Lexical Error
              </button>
              <button className="btn-secondary" onClick={handleClear}>
                Clear
              </button>
            </div>
          </div>

          <div className="editor-container">
            <textarea
              className="code-editor"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="Write or paste your TimetableLang code here..."
              spellCheck={false}
            />
            <div className="editor-footer">
              <div className="slot-input-wrapper">
                <label htmlFor="max-slots">Max Slots constraint (optional):</label>
                <input
                  id="max-slots"
                  type="number"
                  min="1"
                  placeholder="Auto"
                  value={maxSlots}
                  onChange={(e) => setMaxSlots(e.target.value)}
                />
              </div>
              <button
                className="btn-primary"
                onClick={handleCompile}
                disabled={loading || !source.trim()}
              >
                {loading ? 'Compiling...' : '▶ Compile & Verify'}
              </button>
            </div>
          </div>
        </div>

        {/* Results & Inspection Panel */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Compiler Output</span>
            <div className="toolbar-group">
              <button
                className={`tab-btn ${activeTab === 'timetable' ? 'active' : ''}`}
                onClick={() => setActiveTab('timetable')}
              >
                Timetable
              </button>
              <button
                className={`tab-btn ${activeTab === 'ast' ? 'active' : ''}`}
                onClick={() => setActiveTab('ast')}
              >
                AST
              </button>
              <button
                className={`tab-btn ${activeTab === 'symbols' ? 'active' : ''}`}
                onClick={() => setActiveTab('symbols')}
              >
                Symbol Tables
              </button>
              <button
                className={`tab-btn ${activeTab === 'ir' ? 'active' : ''}`}
                onClick={() => setActiveTab('ir')}
              >
                IR (TAC / Quadruples)
              </button>
              <button
                className={`tab-btn ${activeTab === 'tokens' ? 'active' : ''}`}
                onClick={() => setActiveTab('tokens')}
              >
                Tokens
              </button>
              <button
                className={`tab-btn ${activeTab === 'help' ? 'active' : ''}`}
                onClick={() => setActiveTab('help')}
              >
                Language Help
              </button>
            </div>
          </div>

          <div className="tab-content">
            {/* Connection or Client Error */}
            {clientError && (
              <div className="error-card">
                <div className="error-title">⚠ API Connection Error</div>
                <div className="error-message">
                  {clientError}
                  {'\n\nNote: If running locally without Vercel, start the backend server with:\n  python api_server.py\nOr configure VITE_API_BASE_URL.'}
                </div>
              </div>
            )}

            {/* Compiler Phase Rejection Error */}
            {response && !response.success && response.error && (
              <div className="error-card">
                <div className="error-title">
                  ✕ {response.error.category}
                  {response.error.line ? ` (Line ${response.error.line}, Column ${response.error.column})` : ''}
                </div>
                <div className="error-message">{response.error.message}</div>
              </div>
            )}

            {/* TAB: Timetable */}
            {activeTab === 'timetable' && (
              <div>
                {response && response.success && response.stages.timetable ? (
                  <div>
                    <h3 style={{ marginBottom: '1rem', color: 'var(--success)' }}>
                      ✓ Timetable Verified Successfully ({response.stages.timetable.assignments.length} exams across{' '}
                      {response.stages.timetable.slots_used.length} slot(s))
                    </h3>
                    <table className="timetable-table">
                      <thead>
                        <tr>
                          <th>Slot</th>
                          <th>Course</th>
                          <th>Room</th>
                          <th>Invigilator</th>
                          <th>Student Group</th>
                          <th>Type</th>
                        </tr>
                      </thead>
                      <tbody>
                        {response.stages.timetable.assignments.map((item, idx) => (
                          <tr key={idx}>
                            <td>
                              <span className="badge-slot">Slot {item.slot}</span>
                            </td>
                            <td><strong>{item.course}</strong></td>
                            <td>{item.room}</td>
                            <td>{item.invigilator}</td>
                            <td>{item.students || item.student_group}</td>
                            <td style={{ color: item.auto_assigned ? 'var(--accent)' : 'var(--text-muted)' }}>
                              {item.auto_assigned ? 'AUTO' : 'Pinned'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>

                    <h4 style={{ marginTop: '1.5rem', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>
                      Slot-by-Slot Schedule View:
                    </h4>
                    <pre className="code-view">{response.stages.timetable.by_slot}</pre>
                  </div>
                ) : !response ? (
                  <p style={{ color: 'var(--text-muted)' }}>
                    Press "▶ Compile & Verify" to run the source code through the compiler pipeline.
                  </p>
                ) : (
                  <p style={{ color: 'var(--text-muted)' }}>
                    No timetable produced because the compilation failed at the{' '}
                    <strong>{response.stage_failed}</strong> stage.
                  </p>
                )}
              </div>
            )}

            {/* TAB: AST */}
            {activeTab === 'ast' && (
              <div>
                <h4 style={{ marginBottom: '0.5rem', color: 'var(--accent)' }}>Abstract Syntax Tree (AST)</h4>
                {response?.stages.ast?.tree ? (
                  <pre className="code-view">{response.stages.ast.tree}</pre>
                ) : (
                  <p style={{ color: 'var(--text-muted)' }}>No AST available. Run a syntactically valid program.</p>
                )}
              </div>
            )}

            {/* TAB: Symbol Tables */}
            {activeTab === 'symbols' && (
              <div>
                <h4 style={{ marginBottom: '0.5rem', color: 'var(--accent)' }}>Symbol Tables (Types & Global Scope)</h4>
                {response?.stages.semantic?.symbol_tables ? (
                  <pre className="code-view">{response.stages.semantic.symbol_tables}</pre>
                ) : (
                  <p style={{ color: 'var(--text-muted)' }}>No symbol tables available.</p>
                )}
              </div>
            )}

            {/* TAB: IR */}
            {activeTab === 'ir' && (
              <div>
                <h4 style={{ marginBottom: '0.5rem', color: 'var(--accent)' }}>Linear Three-Address Code (TAC)</h4>
                {response?.stages.ir?.tac ? (
                  <pre className="code-view">{response.stages.ir.tac.join('\n')}</pre>
                ) : (
                  <p style={{ color: 'var(--text-muted)' }}>No TAC available.</p>
                )}

                <h4 style={{ marginTop: '1.25rem', marginBottom: '0.5rem', color: 'var(--accent)' }}>
                  Compiler Quadruples (Op, Arg1, Arg2, Result)
                </h4>
                {response?.stages.ir?.quadruples ? (
                  <table className="timetable-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Op</th>
                        <th>Arg1</th>
                        <th>Arg2</th>
                        <th>Result</th>
                      </tr>
                    </thead>
                    <tbody>
                      {response.stages.ir.quadruples.map((q) => (
                        <tr key={q.index}>
                          <td>{q.index}</td>
                          <td style={{ color: 'var(--accent)' }}>{q.op}</td>
                          <td>{q.arg1}</td>
                          <td>{q.arg2}</td>
                          <td><strong>{q.result}</strong></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : null}
              </div>
            )}

            {/* TAB: Tokens */}
            {activeTab === 'tokens' && (
              <div>
                <h4 style={{ marginBottom: '0.5rem', color: 'var(--accent)' }}>Token Stream</h4>
                {response?.stages.lexer?.tokens ? (
                  <pre className="code-view">
                    {response.stages.lexer.tokens
                      .map((t) => `Token(type=${t.type}, value=${JSON.stringify(t.value)}, line=${t.line}, col=${t.column})`)
                      .join('\n')}
                  </pre>
                ) : (
                  <p style={{ color: 'var(--text-muted)' }}>No token stream available.</p>
                )}
              </div>
            )}

            {/* TAB: Language Help */}
            {activeTab === 'help' && (
              <div className="syntax-help">
                <h3 style={{ color: 'var(--text-main)', marginBottom: '0.75rem' }}>TimetableLang Grammar Guide</h3>

                <h4>1. Declarations</h4>
                <p>All declarations terminate with a semicolon <code>;</code>.</p>
                <pre className="code-view">
{`room <identifier> capacity <number>;
invigilator <identifier>;
group <identifier> size <number>;
exam <identifier> room <identifier> invigilator <identifier> students <identifier> slot <number>;`}
                </pre>

                <h4>2. Fixed vs Automatic Slots</h4>
                <ul>
                  <li><strong>slot 1, 2, ...</strong>: Pinned exam slot chosen by the user.</li>
                  <li><strong>slot 0 (AUTO)</strong>: Automatic slot allocation. The compiler backtracks to find a conflict-free slot.</li>
                </ul>

                <h4>3. Validation Rules Enforced</h4>
                <ul>
                  <li>No duplicate declarations of rooms, invigilators, or groups.</li>
                  <li>No undeclared resource references in exams.</li>
                  <li>Room capacity must be greater than or equal to student group size.</li>
                  <li>Zero room double-bookings in the same time slot.</li>
                  <li>Zero invigilator double-bookings in the same time slot.</li>
                  <li>Zero student group clashes in the same time slot.</li>
                </ul>

                <h4>4. Comments</h4>
                <p>Lines or text starting with <code>#</code> are treated as comments and ignored by the lexer.</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        TimetableLang Compiler Project — Compiler Design Laboratory (BCSE307P) | Phase 3 Final Submission
      </footer>
    </div>
  );
};

export default App;
