"""
Interactive Exam Interface HTML template for the Proctoring Kiosk.
Contains 10 professional Computer Vision & AI questions, 15-minute countdown timer,
interactive answer tracking, comprehensive results screen with question review,
and seamless exit capabilities.
"""

EXAM_HTML_CONTENT = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Local proctoring - Экзамен</title>
  <style>
    :root {
      --bg-dark: #0b1120;
      --card-bg: #1e293b;
      --card-hover: #334155;
      --accent-blue: #38bdf8;
      --accent-indigo: #6366f1;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --border-color: #334155;
      --success: #22c55e;
      --warning: #f59e0b;
      --danger: #ef4444;
      --success-bg: rgba(34, 197, 94, 0.12);
      --danger-bg: rgba(239, 68, 68, 0.12);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
      -webkit-user-select: none;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg-dark);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    header {
      background-color: rgba(15, 23, 42, 0.9);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-color);
      padding: 14px 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-logo {
      width: 38px;
      height: 38px;
      background: linear-gradient(135deg, var(--accent-blue), var(--accent-indigo));
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 20px;
      box-shadow: 0 4px 12px rgba(56, 189, 248, 0.25);
    }

    .brand-title h1 {
      font-size: 17px;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: #f8fafc;
    }

    .brand-title p {
      font-size: 12px;
      color: var(--text-muted);
    }

    .exam-meta {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .meta-badge {
      background: rgba(56, 189, 248, 0.1);
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 5px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      color: var(--accent-blue);
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .meta-badge::before {
      content: '';
      width: 8px;
      height: 8px;
      background: var(--success);
      border-radius: 50%;
      box-shadow: 0 0 8px var(--success);
    }

    .timer-pill {
      background-color: #0f172a;
      border: 1px solid var(--border-color);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 700;
      font-family: 'Consolas', 'Courier New', monospace;
      color: #38bdf8;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.3s ease;
    }

    .timer-pill.warning {
      color: var(--warning);
      border-color: var(--warning);
      background-color: rgba(245, 158, 11, 0.1);
    }

    .timer-pill.danger {
      color: var(--danger);
      border-color: var(--danger);
      background-color: rgba(239, 68, 68, 0.15);
      animation: pulse 1s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.6; }
    }

    main {
      flex: 1;
      max-width: 980px;
      width: 100%;
      margin: 24px auto 40px;
      padding: 0 24px;
    }

    /* Top Question Jump Bar */
    .jump-bar {
      display: flex;
      gap: 8px;
      justify-content: center;
      flex-wrap: wrap;
      margin-bottom: 20px;
      background-color: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 12px 16px;
    }

    .jump-btn {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      border: 1px solid var(--border-color);
      background-color: #0f172a;
      color: var(--text-muted);
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;
    }

    .jump-btn:hover {
      background-color: var(--card-hover);
      color: var(--text-main);
      border-color: var(--accent-blue);
    }

    .jump-btn.active {
      background: linear-gradient(135deg, var(--accent-blue), var(--accent-indigo));
      color: white;
      border-color: transparent;
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
    }

    .jump-btn.answered:not(.active) {
      background-color: rgba(56, 189, 248, 0.15);
      color: var(--accent-blue);
      border-color: rgba(56, 189, 248, 0.4);
    }

    .progress-container {
      background-color: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 16px 20px;
      margin-bottom: 24px;
    }

    .progress-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 10px;
      font-size: 13px;
      color: var(--text-muted);
    }

    .progress-bar-bg {
      background-color: #0f172a;
      height: 8px;
      border-radius: 4px;
      overflow: hidden;
    }

    .progress-bar-fill {
      background: linear-gradient(90deg, var(--accent-blue), var(--accent-indigo));
      height: 100%;
      width: 10%;
      transition: width 0.3s ease;
    }

    .question-card {
      background-color: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 30px;
      margin-bottom: 24px;
      box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.4);
    }

    .q-number {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--accent-blue);
      font-weight: 800;
      margin-bottom: 10px;
    }

    .q-text {
      font-size: 18px;
      font-weight: 600;
      line-height: 1.55;
      margin-bottom: 20px;
      color: #f8fafc;
    }

    .code-block {
      background-color: #090d16;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 14px 18px;
      font-family: 'Consolas', 'Courier New', monospace;
      font-size: 13.5px;
      color: #38bdf8;
      margin-bottom: 20px;
      white-space: pre-wrap;
      line-height: 1.45;
    }

    .options-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .option-item {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 15px 20px;
      background-color: rgba(15, 23, 42, 0.65);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .option-item:hover {
      background-color: var(--card-hover);
      border-color: var(--accent-blue);
      transform: translateX(2px);
    }

    .option-item.selected {
      background-color: rgba(56, 189, 248, 0.16);
      border-color: var(--accent-blue);
    }

    .radio-circle {
      width: 20px;
      height: 20px;
      border-radius: 50%;
      border: 2px solid var(--text-muted);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
      flex-shrink: 0;
    }

    .option-item.selected .radio-circle {
      border-color: var(--accent-blue);
    }

    .option-item.selected .radio-circle::after {
      content: '';
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background-color: var(--accent-blue);
    }

    .option-text {
      font-size: 15.5px;
      line-height: 1.4;
    }

    .nav-buttons {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 24px;
      padding-bottom: 20px;
    }

    .nav-left, .nav-right {
      display: flex;
      gap: 12px;
    }

    .btn {
      padding: 12px 24px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .btn-prev {
      background-color: var(--card-bg);
      color: var(--text-main);
      border: 1px solid var(--border-color);
    }

    .btn-prev:hover:not(:disabled) {
      background-color: var(--card-hover);
    }

    .btn-prev:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    .btn-next {
      background: linear-gradient(135deg, var(--accent-blue), var(--accent-indigo));
      color: white;
    }

    .btn-next:hover {
      opacity: 0.95;
      transform: translateY(-1px);
    }

    .btn-finish-red {
      background-color: #dc2626;
      color: white;
      border: 1px solid #ef4444;
      box-shadow: 0 4px 14px rgba(239, 68, 68, 0.4);
    }

    .btn-finish-red:hover {
      background-color: #b91c1c;
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(239, 68, 68, 0.55);
    }

    .btn-top-finish {
      background-color: #dc2626;
      color: #ffffff;
      border: 1px solid #ef4444;
      border-radius: 8px;
      padding: 7px 16px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s ease;
      box-shadow: 0 2px 8px rgba(239, 68, 68, 0.35);
    }

    .btn-top-finish:hover {
      background-color: #b91c1c;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(239, 68, 68, 0.5);
    }

    .btn-exit-app {
      background-color: #dc2626;
      color: #fff;
      font-weight: 700;
      padding: 14px 32px;
      font-size: 16px;
      border: 1px solid #ef4444;
      border-radius: 10px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 10px;
      box-shadow: 0 4px 16px rgba(239, 68, 68, 0.35);
      transition: all 0.2s;
    }

    .btn-exit-app:hover {
      background-color: #b91c1c;
      transform: translateY(-2px);
    }

    /* ------------------------------------------------------------- */
    /* IN-PAGE CONFIRMATION MODAL (NO BROWSER POPUPS)                */
    /* ------------------------------------------------------------- */
    .modal-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      width: 100%;
      height: 100%;
      background: rgba(10, 15, 26, 0.88);
      backdrop-filter: blur(8px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      animation: modalFadeIn 0.2s ease-out;
    }

    .modal-card {
      background: #1e293b;
      border: 1px solid rgba(56, 189, 248, 0.35);
      border-radius: 18px;
      padding: 32px 36px;
      max-width: 480px;
      width: 90%;
      text-align: center;
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.6), 0 0 25px rgba(56, 189, 248, 0.15);
      animation: modalScaleUp 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }

    @keyframes modalFadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    @keyframes modalScaleUp {
      from { transform: scale(0.92); opacity: 0; }
      to { transform: scale(1); opacity: 1; }
    }

    .modal-icon {
      font-size: 44px;
      margin-bottom: 12px;
      line-height: 1;
    }

    .modal-title {
      font-size: 21px;
      font-weight: 800;
      color: #ffffff;
      margin-bottom: 10px;
      letter-spacing: -0.01em;
    }

    .modal-desc {
      font-size: 14px;
      color: #94a3b8;
      line-height: 1.55;
      margin-bottom: 26px;
    }

    .modal-desc strong {
      color: #38bdf8;
    }

    .modal-actions {
      display: flex;
      gap: 14px;
      justify-content: center;
    }

    .btn-modal-cancel {
      background-color: #334155;
      color: #e2e8f0;
      border: 1px solid #475569;
      padding: 11px 22px;
      font-size: 14px;
      font-weight: 600;
      border-radius: 9px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .btn-modal-cancel:hover {
      background-color: #475569;
      color: #ffffff;
      transform: translateY(-1px);
    }

    .btn-modal-confirm {
      padding: 11px 24px;
      font-size: 14px;
      font-weight: 700;
      border-radius: 9px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .btn-modal-confirm.danger {
      background-color: #dc2626;
      color: #ffffff;
      border: 1px solid #ef4444;
      box-shadow: 0 4px 14px rgba(239, 68, 68, 0.4);
    }

    .btn-modal-confirm.danger:hover {
      background-color: #b91c1c;
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(239, 68, 68, 0.55);
    }

    .btn-modal-confirm.primary {
      background-color: #0284c7;
      color: #ffffff;
      border: 1px solid #38bdf8;
      box-shadow: 0 4px 14px rgba(56, 189, 248, 0.35);
    }

    .btn-modal-confirm.primary:hover {
      background-color: #0369a1;
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(56, 189, 248, 0.5);
    }

    /* ------------------------------------------------------------- */
    /* LOGIN (TITLE) VIEW STYLING                                    */
    /* ------------------------------------------------------------- */
    #login-view {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: calc(100vh - 80px);
      padding: 30px 20px;
    }

    .login-card {
      background: linear-gradient(180deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.98));
      border: 1px solid var(--border-color);
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.55), 0 0 35px rgba(56, 189, 248, 0.12);
      border-radius: 20px;
      padding: 44px 40px;
      max-width: 520px;
      width: 100%;
      text-align: center;
      animation: modalFadeIn 0.3s ease-out;
    }

    .login-icon {
      font-size: 50px;
      margin-bottom: 12px;
      line-height: 1;
    }

    .login-title {
      font-size: 23px;
      font-weight: 800;
      color: #ffffff;
      margin-bottom: 6px;
      letter-spacing: -0.02em;
    }

    .login-subtitle {
      font-size: 13.5px;
      color: var(--text-muted);
      margin-bottom: 26px;
      line-height: 1.5;
    }

    .login-field-group {
      text-align: left;
      margin-bottom: 20px;
    }

    .login-field-label {
      display: block;
      font-size: 12.5px;
      font-weight: 700;
      color: var(--accent-blue);
      margin-bottom: 8px;
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }

    .login-input {
      width: 100%;
      background: #090d16;
      border: 1.5px solid var(--border-color);
      border-radius: 10px;
      padding: 14px 18px;
      color: #ffffff;
      font-size: 15px;
      outline: none;
      transition: all 0.2s ease;
    }

    .login-input:focus {
      border-color: var(--accent-blue);
      box-shadow: 0 0 14px rgba(56, 189, 248, 0.3);
      background: #0d1527;
    }

    .login-info-box {
      background: rgba(15, 23, 42, 0.65);
      border: 1px solid rgba(51, 65, 85, 0.6);
      border-radius: 10px;
      padding: 14px 18px;
      margin-bottom: 26px;
      text-align: left;
      font-size: 13px;
      color: #cbd5e1;
      line-height: 1.6;
    }

    .login-info-box ul {
      list-style: none;
      padding-left: 0;
    }

    .login-info-box li {
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .btn-start-exam {
      width: 100%;
      background: linear-gradient(135deg, #0284c7, #4f46e5);
      color: #ffffff;
      border: none;
      border-radius: 12px;
      padding: 16px 28px;
      font-size: 16px;
      font-weight: 800;
      cursor: pointer;
      box-shadow: 0 6px 20px rgba(2, 132, 199, 0.4);
      transition: all 0.25s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
    }

    .btn-start-exam:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 26px rgba(2, 132, 199, 0.6);
      background: linear-gradient(135deg, #0369a1, #4338ca);
    }

    .btn-admin-panel {
      width: 100%;
      margin-top: 14px;
      background: transparent;
      color: #94a3b8;
      border: 1.5px dashed rgba(56, 189, 248, 0.45);
      border-radius: 12px;
      padding: 12px 20px;
      font-size: 13.5px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: all 0.2s ease;
    }

    .btn-admin-panel:hover {
      background: rgba(56, 189, 248, 0.12);
      color: #38bdf8;
      border-color: #38bdf8;
      transform: translateY(-1px);
    }

    .hdr-student-pill {
      background: rgba(30, 41, 59, 0.85);
      border: 1px solid var(--border-color);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 700;
      color: #e2e8f0;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .hdr-q-pill {
      background: #0f172a;
      border: 1px solid var(--border-color);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 700;
      color: var(--accent-blue);
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .proctor-verdict {
      padding: 14px 22px;
      border-radius: 12px;
      font-size: 14.5px;
      font-weight: 700;
      margin: 16px auto 24px;
      max-width: 620px;
      line-height: 1.5;
      text-align: center;
    }

    .proctor-verdict.passed {
      background-color: rgba(34, 197, 94, 0.15);
      border: 1px solid rgba(34, 197, 94, 0.45);
      color: #86efac;
    }

    .proctor-verdict.failed {
      background-color: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.45);
      color: #fca5a5;
    }

    /* ------------------------------------------------------------- */
    /* RESULTS SCREEN STYLING                                        */
    /* ------------------------------------------------------------- */
    #results-view {
      display: none;
    }

    .results-hero {
      background: linear-gradient(180deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95));
      border: 1px solid var(--border-color);
      border-radius: 18px;
      padding: 36px;
      text-align: center;
      margin-bottom: 30px;
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.4);
    }

    .hero-score-badge {
      font-size: 56px;
      font-weight: 900;
      color: #38bdf8;
      letter-spacing: -0.02em;
      margin-bottom: 6px;
      font-family: 'Consolas', monospace;
    }

    .hero-status-tag {
      display: inline-block;
      padding: 6px 18px;
      border-radius: 999px;
      font-weight: 800;
      font-size: 15px;
      margin-bottom: 24px;
    }

    .hero-status-tag.passed {
      background-color: rgba(34, 197, 94, 0.18);
      color: #4ade80;
      border: 1px solid #22c55e;
    }

    .hero-status-tag.failed {
      background-color: rgba(239, 68, 68, 0.18);
      color: #f87171;
      border: 1px solid #ef4444;
    }

    .results-stats-row {
      display: flex;
      justify-content: center;
      gap: 20px;
      flex-wrap: wrap;
      margin-bottom: 28px;
    }

    .stat-card {
      background-color: #0f172a;
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 12px 22px;
      min-width: 140px;
    }

    .stat-card .val {
      font-size: 20px;
      font-weight: 800;
      color: #f8fafc;
      margin-bottom: 2px;
    }

    .stat-card .lbl {
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .results-exit-container {
      display: flex;
      justify-content: center;
      gap: 16px;
      margin-top: 10px;
    }

    .review-title {
      font-size: 20px;
      font-weight: 800;
      margin: 32px 0 16px;
      color: #f8fafc;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .review-card {
      background-color: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 22px;
      margin-bottom: 18px;
    }

    .review-card.correct {
      border-left: 4px solid var(--success);
    }

    .review-card.incorrect {
      border-left: 4px solid var(--danger);
    }

    .review-card.skipped {
      border-left: 4px solid var(--warning);
    }

    .review-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }

    .review-q-title {
      font-size: 14px;
      font-weight: 700;
      color: var(--accent-blue);
    }

    .review-badge {
      font-size: 12px;
      font-weight: 800;
      padding: 4px 10px;
      border-radius: 6px;
    }

    .review-badge.correct {
      background-color: var(--success-bg);
      color: var(--success);
      border: 1px solid rgba(34, 197, 94, 0.4);
    }

    .review-badge.incorrect {
      background-color: var(--danger-bg);
      color: var(--danger);
      border: 1px solid rgba(239, 68, 68, 0.4);
    }

    .review-badge.skipped {
      background-color: rgba(245, 158, 11, 0.12);
      color: var(--warning);
      border: 1px solid rgba(245, 158, 11, 0.4);
    }

    .answer-line {
      padding: 10px 14px;
      border-radius: 8px;
      margin-top: 8px;
      font-size: 14px;
      line-height: 1.4;
    }

    .answer-line.user-correct {
      background-color: var(--success-bg);
      border: 1px solid rgba(34, 197, 94, 0.3);
      color: #86efac;
    }

    .answer-line.user-wrong {
      background-color: var(--danger-bg);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #fca5a5;
    }

    .answer-line.correct-ref {
      background-color: rgba(34, 197, 94, 0.08);
      border: 1px dashed rgba(34, 197, 94, 0.4);
      color: #86efac;
    }

    .review-explanation {
      margin-top: 12px;
      padding: 12px 16px;
      background-color: rgba(15, 23, 42, 0.7);
      border-radius: 8px;
      font-size: 13px;
      line-height: 1.5;
      color: #cbd5e1;
    }

    .review-explanation strong {
      color: var(--accent-blue);
    }

    /* ------------------------------------------------------------- */
    /* RESULTS TABS & INCIDENTS APPEAL STYLING                       */
    /* ------------------------------------------------------------- */
    .results-tab-bar {
      display: flex;
      gap: 12px;
      margin-bottom: 24px;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 12px;
    }

    .res-tab-btn {
      background-color: #1e293b;
      color: #94a3b8;
      border: 1px solid var(--border-color);
      padding: 10px 22px;
      border-radius: 10px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
    }

    .res-tab-btn:hover {
      color: #f8fafc;
      background-color: #334155;
    }

    .res-tab-btn.active {
      background-color: #0284c7;
      color: #ffffff;
      border-color: #38bdf8;
      box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35);
    }

    .incidents-clean-card {
      background: linear-gradient(180deg, rgba(34, 197, 94, 0.1), rgba(15, 23, 42, 0.8));
      border: 1px dashed rgba(34, 197, 94, 0.4);
      border-radius: 14px;
      padding: 32px;
      text-align: center;
      margin-bottom: 24px;
    }

    .incidents-alert-banner {
      background: rgba(245, 158, 11, 0.1);
      border: 1px solid rgba(245, 158, 11, 0.3);
      border-radius: 10px;
      padding: 12px 18px;
      margin-bottom: 20px;
      font-size: 13.5px;
      color: #fde68a;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .incident-appeal-card {
      background-color: var(--card-bg);
      border: 1px solid var(--border-color);
      border-left: 4px solid var(--danger);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 18px;
      transition: all 0.2s ease;
    }

    .incident-appeal-card.attention {
      border-left-color: var(--warning);
    }

    .incident-card-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }

    .inc-type-tag {
      font-size: 14.5px;
      font-weight: 700;
      color: #38bdf8;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .inc-sev-tag {
      font-size: 11.5px;
      font-weight: 800;
      padding: 3px 10px;
      border-radius: 6px;
      text-transform: uppercase;
    }

    .inc-sev-tag.critical {
      background-color: rgba(239, 68, 68, 0.2);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.4);
    }

    .inc-sev-tag.high, .inc-sev-tag.medium {
      background-color: rgba(245, 158, 11, 0.2);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.4);
    }

    .incident-card-body {
      display: flex;
      gap: 18px;
      align-items: flex-start;
    }

    .incident-thumb {
      width: 150px;
      height: 100px;
      background-color: #020617;
      border-radius: 8px;
      border: 1px solid #334155;
      object-fit: cover;
      cursor: pointer;
      transition: transform 0.2s ease;
      flex-shrink: 0;
    }

    .incident-thumb:hover {
      transform: scale(1.03);
      border-color: #38bdf8;
    }

    .incident-info-col {
      flex: 1;
    }

    .incident-desc {
      font-size: 14px;
      color: #e2e8f0;
      line-height: 1.5;
      margin-bottom: 12px;
    }

    .incident-meta-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      font-size: 12px;
      color: #94a3b8;
    }

    .meta-sub-pill {
      background: #0f172a;
      border: 1px solid #334155;
      padding: 4px 10px;
      border-radius: 6px;
      font-weight: 600;
    }

    .appeal-action-area {
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px solid rgba(51, 65, 85, 0.6);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
    }

    .btn-appeal {
      background: linear-gradient(135deg, rgba(2, 132, 199, 0.25), rgba(99, 102, 241, 0.25));
      color: #38bdf8;
      border: 1.5px solid rgba(56, 189, 248, 0.55);
      border-radius: 8px;
      padding: 9px 20px;
      font-size: 13.5px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
    }

    .btn-appeal:hover {
      background: rgba(56, 189, 248, 0.3);
      border-color: #38bdf8;
      transform: translateY(-1px);
      box-shadow: 0 4px 14px rgba(56, 189, 248, 0.25);
    }

    .appeal-box {
      background-color: #0f172a;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 12px 16px;
      width: 100%;
    }

    .appeal-box.pending {
      border-color: rgba(245, 158, 11, 0.5);
      background-color: rgba(245, 158, 11, 0.08);
    }

    .appeal-box.approved {
      border-color: rgba(34, 197, 94, 0.5);
      background-color: rgba(34, 197, 94, 0.08);
    }

    .appeal-box.rejected {
      border-color: rgba(239, 68, 68, 0.5);
      background-color: rgba(239, 68, 68, 0.08);
    }

    .appeal-badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 800;
      margin-bottom: 6px;
    }

    .appeal-badge.pending {
      background-color: rgba(245, 158, 11, 0.25);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.5);
    }

    .appeal-badge.approved {
      background-color: rgba(34, 197, 94, 0.25);
      color: #4ade80;
      border: 1px solid rgba(34, 197, 94, 0.5);
    }

    .appeal-badge.rejected {
      background-color: rgba(239, 68, 68, 0.25);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.5);
    }

    .appeal-meta {
      font-size: 12.5px;
      color: #cbd5e1;
      line-height: 1.5;
    }

    /* Modal Form Styles */
    .appeal-modal-card {
      max-width: 620px;
      width: 90%;
      text-align: left;
    }

    .btn-close-modal {
      background: transparent;
      border: none;
      color: #94a3b8;
      font-size: 18px;
      cursor: pointer;
      padding: 4px;
      line-height: 1;
    }

    .btn-close-modal:hover {
      color: #f8fafc;
    }

    .appeal-image-container {
      background: #020617;
      border: 1px solid #334155;
      border-radius: 10px;
      padding: 8px;
      text-align: center;
      margin: 12px 0 18px;
    }

    .appeal-image-container img {
      max-height: 230px;
      max-width: 100%;
      object-fit: contain;
      border-radius: 6px;
    }

    .appeal-form-group {
      margin-bottom: 16px;
    }

    .appeal-label {
      display: block;
      font-size: 13px;
      font-weight: 700;
      color: #94a3b8;
      margin-bottom: 6px;
    }

    .appeal-select {
      width: 100%;
      background: #0f172a;
      border: 1px solid #334155;
      color: #f8fafc;
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 14px;
      outline: none;
      cursor: pointer;
    }

    .appeal-select:focus {
      border-color: #38bdf8;
      box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
    }

    .appeal-textarea {
      width: 100%;
      background: #0f172a;
      border: 1px solid #334155;
      color: #f8fafc;
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 14px;
      line-height: 1.5;
      outline: none;
      resize: vertical;
      font-family: inherit;
    }

    .appeal-textarea:focus {
      border-color: #38bdf8;
      box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
    }
  </style>
</head>
<body oncontextmenu="return false;">
  <header id="exam-header" style="display: none;">
    <div class="brand">
      <div class="brand-logo">🛡️</div>
      <div class="brand-title">
        <h1>Система локального прокторинга</h1>
        <p>Тестирование: Компьютерное зрение & Системы ИИ</p>
      </div>
    </div>
    <div class="hdr-student-pill">
      <span>👤</span> <strong id="hdr-student-name">Студент</strong>
    </div>
    <div class="exam-meta">
      <div class="hdr-q-pill">Вопрос <strong id="hdr-q-curr">1</strong> из <strong id="hdr-q-total">10</strong></div>
      <div class="timer-pill" id="timer">⏱️ 15:00</div>
    </div>
  </header>

  <main>
    <!-- 1. LOGIN / TITLE SCREEN -->
    <div id="login-view">
      <div class="login-card">
        <div class="login-icon">🛡️</div>
        <h1 class="login-title">Система локального прокторинга</h1>
        <p class="login-subtitle">Автоматизированный мониторинг и защита экзаменационного процесса</p>

        <div class="login-field-group">
          <label class="login-field-label" for="student-name-input">ФИО студента (тестируемого):</label>
          <input type="text" id="student-name-input" class="login-input" placeholder="Введите фамилию, имя и отчество..." autofocus autocomplete="off">
        </div>

        <div class="login-info-box">
          <ul>
            <li>⏱️ <strong>Регламент:</strong> 15 минут на прохождение 10 вопросов</li>
            <li>📷 <strong>Прокторинг:</strong> Анализ взгляда, положения головы и детекция устройств</li>
            <li>🔒 <strong>Безопасность:</strong> Полноэкранный режим с контролем фокуса окна</li>
          </ul>
        </div>

        <button type="button" class="btn-start-exam" id="btn-start-exam" onclick="submitLoginAndStart()">
          Начать тестирование →
        </button>

        <button type="button" class="btn-admin-panel" id="btn-open-admin" onclick="openAdminDashboard()">
          🎓 Панель преподавателя (Admin Dashboard)
        </button>
      </div>
    </div>

    <!-- 2. ACTIVE EXAM CONTAINER -->
    <div id="exam-view" style="display: none;">
      <!-- Fast Question Navigation Pills (1 to 10) -->
      <div class="jump-bar" id="jump-bar"></div>

      <!-- Progress bar -->
      <div class="progress-container">
        <div class="progress-header">
          <span>Вопрос <strong id="q-curr">1</strong> из <strong id="q-total">10</strong></span>
          <span id="answered-count">Отвечено: 0 / 10</span>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" id="p-bar"></div>
        </div>
      </div>

      <!-- Question Card -->
      <div class="question-card" id="question-container"></div>

      <!-- Navigation buttons -->
      <div class="nav-buttons">
        <div class="nav-left">
          <button class="btn btn-prev" id="btn-prev" onclick="prevQuestion()">← Предыдущий</button>
        </div>
        <div class="nav-right" style="display: flex; gap: 12px;">
          <button class="btn btn-next" id="btn-next" onclick="nextQuestion()">Следующий →</button>
          <button class="btn btn-finish-red" id="btn-finish" onclick="openFinishConfirmModal()">Завершить 🏁</button>
        </div>
      </div>
    </div>

    <!-- 3. EXAM RESULTS CONTAINER -->
    <div id="results-view" style="display: none;">
      <div class="results-hero">
        <div style="font-size: 15px; color: #94a3b8; margin-bottom: 8px;">
          Студент: <strong id="res-student-name" style="color: #f8fafc; font-size: 16px;">Студент</strong>
        </div>
        <div class="hero-score-badge" id="res-score-text">0 / 10</div>
        <div class="hero-status-tag" id="res-status-tag">ТЕСТ СДАН</div>

        <!-- Proctoring Verdict -->
        <div class="proctor-verdict passed" id="res-proctor-verdict">
          🟢 <strong>Прокторинг: Тест сдан честно</strong> — нарушений регламента не зафиксировано
        </div>

        <div class="results-stats-row">
          <div class="stat-card">
            <div class="val" id="res-stat-time">00:00</div>
            <div class="lbl">Время экзамена</div>
          </div>
          <div class="stat-card">
            <div class="val" id="res-stat-correct" style="color: #4ade80;">0</div>
            <div class="lbl">Правильных</div>
          </div>
          <div class="stat-card">
            <div class="val" id="res-stat-wrong" style="color: #f87171;">0</div>
            <div class="lbl">Ошибок</div>
          </div>
          <div class="stat-card">
            <div class="val" id="res-stat-pct" style="color: #38bdf8;">0%</div>
            <div class="lbl">Результат</div>
          </div>
        </div>

        <div class="results-exit-container">
          <button class="btn-exit-app" onclick="exitExam()">
            🚪 Выйти из программы
          </button>
          <button class="btn btn-prev" onclick="restartExam()" style="padding: 14px 24px; font-size: 15px;">
            🔄 Пройти заново
          </button>
        </div>
      </div>

      <!-- Results Tab Bar: Incidents & Appeals / Review -->
      <div class="results-tab-bar">
        <button type="button" class="res-tab-btn active" id="tab-incidents-btn" onclick="switchResultsTab('incidents')">
          🛡️ Протокол нарушений и апелляция (<span id="res-incidents-count">0</span>)
        </button>
        <button type="button" class="res-tab-btn" id="tab-review-btn" onclick="switchResultsTab('review')">
          📋 Разбор ответов теста (10)
        </button>
      </div>

      <!-- TAB 1: Incidents & Appeals -->
      <div id="incidents-tab-content">
        <div id="incidents-empty-card" class="incidents-clean-card" style="display: none;">
          <div style="font-size: 32px; margin-bottom: 8px;">🟢</div>
          <div style="font-size: 17px; font-weight: 800; color: #4ade80;">Тестирование пройдено без нарушений!</div>
          <div style="color: #94a3b8; font-size: 13.5px; margin-top: 4px;">Система прокторинга не зафиксировала отклонений от регламента. Подача апелляции не требуется.</div>
        </div>
        <div id="incidents-alert-banner" class="incidents-alert-banner" style="display: none;">
          <span>ℹ️</span>
          <span>Вы можете оспорить зафиксированные нарушения регламента и прикрепить пояснение для преподавателя до закрытия программы.</span>
        </div>
        <div id="incidents-list-container"></div>
      </div>

      <!-- TAB 2: Question Review -->
      <div id="review-tab-content" style="display: none;">
        <div class="review-title">
          <span>📋 Подробный разбор каждого вопроса:</span>
        </div>
        <div id="review-cards-list"></div>
      </div>

      <div style="text-align: center; margin: 30px 0;">
        <button class="btn-exit-app" onclick="exitExam()">
          🚪 Выйти из программы
        </button>
      </div>
    </div>
  </main>

  <script>
    const TOTAL_TIME_SECONDS = 15 * 60; // 15:00 minutes
    let timeRemaining = TOTAL_TIME_SECONDS;
    let timerInterval = null;
    let examFinished = false;

    const questions = [
      {
        id: 1,
        title: "Архитектура детекции: YOLOv8",
        text: "Какое ключевое архитектурное отличие детектора YOLOv8 от YOLOv5 позволяет повысить скорость сходимости и точность позиционирования боксов?",
        options: [
          "Использование классификатора Виолы-Джонса с интегральным изображением",
          "Переход к Anchor-Free парадигме и разделенной голове (Decoupled Head) для классов и боксов",
          "Замена всех сверток на полносвязные слои многослойного перцептрона (MLP)",
          "Применение двухстадийного Region Proposal Network (RPN)"
        ],
        correct: 1,
        explanation: "YOLOv8 является Anchor-Free детектором, предсказывающим центр объекта напрямую без привязки к фиксированным шаблонам, и использует независимые ветки (Decoupled Head) для классификации и регрессии боксов."
      },
      {
        id: 2,
        title: "Оценка позы головы (Perspective-n-Point)",
        text: "Какая функция библиотеки OpenCV решает задачу Perspective-n-Point по сопоставленным 2D-точкам лица и канонической 3D-модели?",
        code: "success, rvec, tvec = cv2.solvePnP(object_3d, points_2d, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE)",
        options: [
          "cv2.solvePnP — вычисление векторов поворота (rvec) и перемещения (tvec)",
          "cv2.findHomography — расчет проективной гомографии между двумя плоскостями",
          "cv2.warpAffine — аффинное преобразование изображения по 3 опорным точкам",
          "cv2.drawContours — отрисовка замкнутых бинарных контуров"
        ],
        correct: 0,
        explanation: "cv2.solvePnP находит пространственное положение объекта по набору 3D-координат эталонной модели и их 2D-проекциям на матрицу камеры с использованием итеративного алгоритма Левенберга-Марквардта."
      },
      {
        id: 3,
        title: "Трекинг взгляда: Координаты радужки (Iris)",
        text: "В MediaPipe FaceMesh при активации refine_landmarks=True, какие индексы отвечают за центры радужки (Iris centers) левого и правого глаза?",
        options: [
          "Индексы 33 и 263 (внешние уголки глаз)",
          "Индексы 1 и 152 (кончик носа и центр подбородка)",
          "Индексы 468 (левый зрачок) и 473 (правый зрачок)",
          "Индексы 61 и 291 (уголки рта)"
        ],
        correct: 2,
        explanation: "Модель MediaPipe расширяет 468 лицевых точек до 478 при refine_landmarks=True: индексы 468 и 473 задают центры зрачков левого и правого глаза для оценки направления взгляда."
      },
      {
        id: 4,
        title: "Безопасность Kiosk Mode (WinAPI)",
        text: "Какой системный механизм Windows позволяет приложению глобально подавлять системные комбинации клавиш (Alt+Tab, Win Key, Alt+F4, Ctrl+Shift+Esc) на низком уровне?",
        options: [
          "Низкоуровневый хук клавиатуры WH_KEYBOARD_LL через функцию SetWindowsHookExW",
          "Переопределение стандартного метода keyPressEvent в главном виджете",
          "Изменение системного реестра HKEY_LOCAL_MACHINE при запуске приложения",
          "Отключение системных служб Windows Update и Print Spooler"
        ],
        correct: 0,
        explanation: "SetWindowsHookExW с флагом WH_KEYBOARD_LL устанавливает глобальный низкоуровневый фильтр, перехватывающий нажатия клавиш до того, как их обработает оболочка Windows Shell."
      },
      {
        id: 5,
        title: "Временная фильтрация аномалий (Debouncing)",
        text: "Зачем в системах видеопрокторинга применяется временная задержка удержания (например, 1.5 секунды) перед фиксацией отвода взгляда или головы?",
        options: [
          "Для искусственного снижения энергопотребления видеокарты",
          "Для исключения ложных срабатываний от естественного моргания, саккад глаз и микродвижений студента",
          "Для шифрования видеопотока перед отправкой на сервер",
          "Из-за ограничений пропускной способности USB 2.0"
        ],
        correct: 1,
        explanation: "Человек постоянно моргает (100–300 мс) и переводит взгляд по монитору. Временной порог удержания (1.5с) гарантирует фиксацию только умышленных отводов внимания от экрана."
      },
      {
        id: 6,
        title: "Сглаживание углов Эйлера (EMA Filter)",
        text: "Какая формула описывает алгоритм экспоненциального скользящего среднего (EMA) для подавления дрожания углов поворота головы?",
        code: "smoothed_angle = alpha * raw_angle + (1.0 - alpha) * prev_smoothed",
        options: [
          "Медианная фильтрация по скользящему окну нечетной длины",
          "Дискретное преобразование Фурье с прямоугольным окном",
          "Интерполяция бикубическими сплайнами Эрмита",
          "Экспоненциальное скользящее среднее (EMA) 1-го порядка с фактором сглаживания alpha"
        ],
        correct: 3,
        explanation: "Формула smoothed = alpha * raw + (1 - alpha) * prev реализует экспоненциальный фильтр: при alpha=0.3 высокочастотный тремор камеры сглаживается, сохраняя отзывчивость на реальные движения."
      },
      {
        id: 7,
        title: "Внутренние параметры камеры (Intrinsics Matrix)",
        text: "Какие параметры входят в матрицу внутренних параметров камеры (Camera Matrix K) в OpenCV?",
        code: "K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=np.float64)",
        options: [
          "Фокусные расстояния fx, fy в пикселях и оптический центр изображения (cx, cy)",
          "Углы крена, тангажа и рыскания (Yaw, Pitch, Roll) в радианах",
          "Коэффициенты радиальной и тангенциальной дисторсии k1, k2, p1, p2",
          "Разрешение матрицы сенсора в мегапикселях и уровень экспозиции"
        ],
        correct: 0,
        explanation: "Матрица K описывает оптическую геометрию камеры: фокусные расстояния fx и fy по осям сенсора в пикселях, а cx и cy — координаты оптической оси на изображении."
      },
      {
        id: 8,
        title: "Контроль целостности среды (OS Focus Monitoring)",
        text: "Какая функция Windows API используется фоновым потоком безопасности для выявления попыток студента переключиться на стороннее приложение?",
        options: [
          "GetCurrentDirectoryW — получение пути к текущей рабочей папке",
          "VirtualAllocEx — выделение виртуальной памяти в чужом адресном пространстве",
          "GetForegroundWindow — получение дескриптора (HWND) активного окна переднего плана",
          "CreateProcessW — запуск нового дочернего изолированного процесса"
        ],
        correct: 2,
        explanation: "GetForegroundWindow возвращает HWND активного окна пользователя. Если дескриптор отличается от окна kiosk-системы, фиксируется событие FOCUS_LOST и экран блокируется защитной шторкой."
      },
      {
        id: 9,
        title: "Многопоточность в Qt (PyQt & QThread)",
        text: "Почему видеозахват и ресурсоемкий инференс нейросетей YOLO и MediaPipe необходимо выносить в отдельный рабочий поток (QThread)?",
        options: [
          "Инференс нейросетей блокирует цикл обработки событий Qt (Event Loop), приводя к зависанию интерфейса",
          "OpenCV аварийно завершает работу при запуске в основном потоке программы",
          "Python на уровне компилятора запрещает отображать видео и виджеты одновременно",
          "Это требование стандарта шифрования SSL/TLS для образовательных порталов"
        ],
        correct: 0,
        explanation: "Графический интерфейс Qt управляется главным циклом событий (QEventLoop). Вычисления инференса (15–40 мс) в главном потоке вызывают зависание UI (Not Responding). Вынос в QThread гарантирует 60 FPS интерфейса."
      },
      {
        id: 10,
        title: "Формат доказательной базы инцидентов (Audit Logging)",
        text: "Какое ключевое преимущество формата JSONL (JSON Lines) перед монолитным JSON-файлом при логировании инцидентов прокторинга?",
        options: [
          "JSONL автоматически сжимает изображения встроенным алгоритмом PNG",
          "Каждая запись дописывается отдельной строкой с немедленным сбросом буфера (flush), защищая от потери данных при сбое",
          "Файлы JSONL могут читаться исключительно учетной записью администратора",
          "JSONL позволяет выполнять быстрые SQL-запросы без создания индексов"
        ],
        correct: 1,
        explanation: "Формат JSON Lines (JSONL) идеален для потокового аудита: каждое событие пишется в конец файла одной строкой и сразу сбрасывается на диск через flush(), гарантируя сохранность истории даже при аварийном завершении."
      }
    ];

    let currentIndex = 0;
    let selectedAnswers = {}; // { qIndex: optionIndex }

    function startTimer() {
      if (timerInterval) clearInterval(timerInterval);
      timerInterval = setInterval(() => {
        if (examFinished) return;
        timeRemaining--;
        updateTimerDisplay();

        if (timeRemaining <= 0) {
          clearInterval(timerInterval);
          finishExam();
        }
      }, 1000);
      updateTimerDisplay();
    }

    function updateTimerDisplay() {
      const mins = Math.floor(Math.max(0, timeRemaining) / 60);
      const secs = Math.max(0, timeRemaining) % 60;
      const fmt = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
      const timerEl = document.getElementById('timer');
      timerEl.innerText = `⏱️ ${fmt}`;

      if (timeRemaining <= 30) {
        timerEl.className = 'timer-pill danger';
      } else if (timeRemaining <= 120) {
        timerEl.className = 'timer-pill warning';
      } else {
        timerEl.className = 'timer-pill';
      }
    }

    function renderJumpBar() {
      const container = document.getElementById('jump-bar');
      let html = '';
      for (let i = 0; i < questions.length; i++) {
        const isAnswered = selectedAnswers.hasOwnProperty(i);
        const isActive = (i === currentIndex);
        let classes = 'jump-btn';
        if (isActive) classes += ' active';
        if (isAnswered) classes += ' answered';
        html += `<button class="${classes}" onclick="jumpToQuestion(${i})">${i + 1}</button>`;
      }
      container.innerHTML = html;
    }

    function jumpToQuestion(index) {
      if (index >= 0 && index < questions.length) {
        currentIndex = index;
        renderQuestion();
      }
    }

    let studentName = "Студент";

    function openAdminDashboard() {
      try {
        window.location.href = "proctor://open_admin";
      } catch (e) {}
    }

    function submitLoginAndStart() {
      const input = document.getElementById('student-name-input');
      const val = (input && input.value) ? input.value.trim() : "";
      if (val.length > 0) {
        studentName = val;
      } else {
        studentName = "Студент (Демо)";
      }

      const hdrStudent = document.getElementById('hdr-student-name');
      if (hdrStudent) hdrStudent.innerText = studentName;
      const resStudent = document.getElementById('res-student-name');
      if (resStudent) resStudent.innerText = studentName;

      // Notify Python proctoring system of student session start
      try {
        window.location.href = "proctor://start?name=" + encodeURIComponent(studentName);
      } catch (e) {}

      document.getElementById('login-view').style.display = 'none';
      document.getElementById('exam-header').style.display = 'flex';
      document.getElementById('exam-view').style.display = 'block';

      renderQuestion();
      startTimer();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function setProctoringViolationsCount(count) {
      const verdictEl = document.getElementById('res-proctor-verdict');
      if (!verdictEl) return;
      if (count === 0) {
        verdictEl.className = 'proctor-verdict passed';
        verdictEl.innerHTML = '🟢 <strong>Прокторинг: Тест сдан честно</strong> — нарушений регламента не зафиксировано';
      } else {
        verdictEl.className = 'proctor-verdict failed';
        verdictEl.innerHTML = `🔴 <strong>Прокторинг: Зафиксированы нарушения (${count})</strong> — зарегистрированы отклонения от регламента`;
      }
    }

    function renderQuestion() {
      const q = questions[currentIndex];
      document.getElementById('q-curr').innerText = currentIndex + 1;
      document.getElementById('q-total').innerText = questions.length;
      const hdrCurr = document.getElementById('hdr-q-curr');
      if (hdrCurr) hdrCurr.innerText = currentIndex + 1;
      const hdrTotal = document.getElementById('hdr-q-total');
      if (hdrTotal) hdrTotal.innerText = questions.length;
      document.getElementById('p-bar').style.width = `${((currentIndex + 1) / questions.length) * 100}%`;

      document.getElementById('btn-prev').disabled = (currentIndex === 0);

      const btnNext = document.getElementById('btn-next');
      const isLast = (currentIndex === questions.length - 1);
      if (isLast) {
        btnNext.innerHTML = 'Завершить тест 🏁';
        btnNext.className = 'btn btn-finish-red';
        btnNext.onclick = confirmFinishExam;
        btnNext.disabled = false;
      } else {
        btnNext.innerHTML = 'Следующий →';
        btnNext.className = 'btn btn-next';
        btnNext.onclick = nextQuestion;
        btnNext.disabled = false;
      }

      let html = `
        <div class="q-number">Вопрос ${currentIndex + 1} из ${questions.length} • ${q.title}</div>
        <div class="q-text">${q.text}</div>
      `;

      if (q.code) {
        html += `<div class="code-block">${q.code}</div>`;
      }

      html += `<div class="options-list">`;
      q.options.forEach((opt, idx) => {
        const isSelected = selectedAnswers[currentIndex] === idx ? 'selected' : '';
        html += `
          <div class="option-item ${isSelected}" onclick="selectOption(${idx})">
            <div class="radio-circle"></div>
            <div class="option-text">${opt}</div>
          </div>
        `;
      });
      html += `</div>`;

      document.getElementById('question-container').innerHTML = html;
      updateAnsweredCount();
      renderJumpBar();
    }

    function selectOption(idx) {
      selectedAnswers[currentIndex] = idx;
      renderQuestion();
    }

    function prevQuestion() {
      if (currentIndex > 0) {
        currentIndex--;
        renderQuestion();
      }
    }

    function nextQuestion() {
      if (currentIndex < questions.length - 1) {
        currentIndex++;
        renderQuestion();
      }
    }

    function updateAnsweredCount() {
      const count = Object.keys(selectedAnswers).length;
      document.getElementById('answered-count').innerText = `Отвечено: ${count} / ${questions.length}`;
    }

    function confirmFinishExam() {
      openFinishConfirmModal();
    }

    function openFinishConfirmModal() {
      const answered = Object.keys(selectedAnswers).length;
      const total = questions.length;
      const modal = document.getElementById('confirm-modal');
      const titleEl = document.getElementById('modal-title');
      const descEl = document.getElementById('modal-desc');
      const iconEl = document.getElementById('modal-icon');
      const confirmBtn = document.getElementById('btn-modal-confirm');

      if (answered < total) {
        // Less than 10 questions answered
        iconEl.innerText = "⚠️";
        titleEl.innerText = "Вы хотите завершить тест досрочно?";
        descEl.innerHTML = `Вы ответили только на <strong>${answered}</strong> из <strong>${total}</strong> вопросов.<br>Неотвеченные вопросы будут засчитаны как неверные.`;
        confirmBtn.innerText = "Да, завершить досрочно";
        confirmBtn.className = "btn-modal-confirm danger";
      } else {
        // All 10 questions answered
        iconEl.innerText = "🏁";
        titleEl.innerText = "Завершить тест?";
        descEl.innerHTML = `Вы ответили на все <strong>${total}</strong> вопросов.<br>Подтвердите завершение для подсчета баллов и перехода к результатам.`;
        confirmBtn.innerText = "Завершить тест";
        confirmBtn.className = "btn-modal-confirm primary";
      }

      modal.style.display = 'flex';
    }

    function closeConfirmModal() {
      const modal = document.getElementById('confirm-modal');
      if (modal) modal.style.display = 'none';
    }

    function executeFinishExam() {
      closeConfirmModal();
      finishExam();
    }

    let examFinishedHandled = false;
    function finishExam() {
      if (examFinishedHandled) return;
      examFinishedHandled = true;
      examFinished = true;
      closeConfirmModal();
      if (timerInterval) clearInterval(timerInterval);

      // Compute statistics
      let correctCount = 0;
      let wrongCount = 0;
      let unansweredCount = 0;

      questions.forEach((q, idx) => {
        if (selectedAnswers.hasOwnProperty(idx)) {
          if (selectedAnswers[idx] === q.correct) {
            correctCount++;
          } else {
            wrongCount++;
          }
        } else {
          unansweredCount++;
        }
      });

      const total = questions.length;
      const scorePct = Math.round((correctCount / total) * 100);
      const timeSpentSec = TOTAL_TIME_SECONDS - Math.max(0, timeRemaining);
      const spentMins = Math.floor(timeSpentSec / 60);
      const spentSecs = timeSpentSec % 60;
      const spentFmt = `${String(spentMins).padStart(2, '0')}:${String(spentSecs).padStart(2, '0')}`;

      // Update hero
      document.getElementById('res-score-text').innerText = `${correctCount} / ${total}`;
      const statusTag = document.getElementById('res-status-tag');
      if (scorePct >= 80) {
        statusTag.className = 'hero-status-tag passed';
        statusTag.innerText = `🏆 ОТЛИЧНО! Тест успешно сдан (${scorePct}%)`;
      } else if (scorePct >= 60) {
        statusTag.className = 'hero-status-tag passed';
        statusTag.innerText = `👍 ХОРОШО! Тест сдан (${scorePct}%)`;
      } else {
        statusTag.className = 'hero-status-tag failed';
        statusTag.innerText = `⚠️ ТЕСТ НЕ СДАН! Менее 60% (${scorePct}%)`;
      }

      document.getElementById('res-stat-time').innerText = spentFmt;
      document.getElementById('res-stat-correct').innerText = `${correctCount}`;
      document.getElementById('res-stat-wrong').innerText = `${wrongCount + unansweredCount}`;
      document.getElementById('res-stat-pct').innerText = `${scorePct}%`;

      // Render detailed review for each question
      let reviewHtml = '';
      questions.forEach((q, idx) => {
        const hasAnswer = selectedAnswers.hasOwnProperty(idx);
        const userChoice = hasAnswer ? selectedAnswers[idx] : null;
        const isCorrect = (userChoice === q.correct);

        let cardClass = 'review-card';
        let badgeClass = 'review-badge';
        let badgeText = '';

        if (!hasAnswer) {
          cardClass += ' skipped';
          badgeClass += ' skipped';
          badgeText = '— НЕ ОТВЕЧЕНО (0)';
        } else if (isCorrect) {
          cardClass += ' correct';
          badgeClass += ' correct';
          badgeText = '✓ ВЕРНО (+1)';
        } else {
          cardClass += ' incorrect';
          badgeClass += ' incorrect';
          badgeText = '✗ НЕВЕРНО (0)';
        }

        reviewHtml += `
          <div class="${cardClass}">
            <div class="review-card-header">
              <span class="review-q-title">Вопрос ${idx + 1}: ${q.title}</span>
              <span class="${badgeClass}">${badgeText}</span>
            </div>
            <div style="font-weight: 600; font-size: 15px; margin-bottom: 10px;">${q.text}</div>
        `;

        if (q.code) {
          reviewHtml += `<div class="code-block" style="padding: 10px 14px; font-size: 12.5px;">${q.code}</div>`;
        }

        if (hasAnswer) {
          const userText = q.options[userChoice];
          if (isCorrect) {
            reviewHtml += `<div class="answer-line user-correct"><strong>Ваш ответ:</strong> ✓ ${userText}</div>`;
          } else {
            reviewHtml += `
              <div class="answer-line user-wrong"><strong>Ваш ответ:</strong> ✗ ${userText}</div>
              <div class="answer-line correct-ref"><strong>Правильный ответ:</strong> ✓ ${q.options[q.correct]}</div>
            `;
          }
        } else {
          reviewHtml += `
            <div class="answer-line user-wrong" style="background: rgba(245, 158, 11, 0.1); color: #fcd34d;"><strong>Ваш ответ:</strong> Вопрос был пропущен</div>
            <div class="answer-line correct-ref"><strong>Правильный ответ:</strong> ✓ ${q.options[q.correct]}</div>
          `;
        }

        reviewHtml += `
            <div class="review-explanation">
              <strong>💡 Разбор и пояснение:</strong> ${q.explanation}
            </div>
          </div>
        `;
      });

      document.getElementById('review-cards-list').innerHTML = reviewHtml;

      // Switch view
      const examHeader = document.getElementById('exam-header');
      if (examHeader) examHeader.style.display = 'none';
      document.getElementById('exam-view').style.display = 'none';
      document.getElementById('results-view').style.display = 'block';
      window.scrollTo({ top: 0, behavior: 'smooth' });

      // Signal Python proctoring system that exam is finished so session report is saved and all alerts/locks/popups are silenced
      try {
        window.location.href = `proctor://finished?name=${encodeURIComponent(studentName)}&correct=${correctCount}&total=${total}&scorePct=${scorePct}&spent=${encodeURIComponent(spentFmt)}`;
      } catch (e) {}
    }

    function exitExam() {
      // Allows user to exit the proctoring app seamlessly without admin password
      try {
        window.location.href = "proctor://exit";
      } catch (e) {}
      try {
        window.close();
      } catch (e) {}
    }

    function restartExam() {
      examFinishedHandled = false;
      examFinished = false;
      activeIncidentsList = [];
      currentAppealingIncidentId = null;
      closeConfirmModal();
      closeAppealModal();
      timeRemaining = TOTAL_TIME_SECONDS;
      selectedAnswers = {};
      currentIndex = 0;
      document.getElementById('results-view').style.display = 'none';
      const examHeader = document.getElementById('exam-header');
      if (examHeader) examHeader.style.display = 'flex';
      document.getElementById('exam-view').style.display = 'block';
      startTimer();
      renderQuestion();
      window.scrollTo({ top: 0, behavior: 'smooth' });

      try {
        window.location.href = "proctor://restarted";
      } catch (e) {}
    }

    // -------------------------------------------------------------
    // INCIDENTS PROTOCOL & STUDENT APPEAL JAVASCRIPT
    // -------------------------------------------------------------
    let activeIncidentsList = [];
    let currentAppealingIncidentId = null;

    function escapeHtml(text) {
      if (!text) return "";
      return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }

    function switchResultsTab(tab) {
      const btnIncidents = document.getElementById('tab-incidents-btn');
      const btnReview = document.getElementById('tab-review-btn');
      const contentIncidents = document.getElementById('incidents-tab-content');
      const contentReview = document.getElementById('review-tab-content');

      if (tab === 'incidents') {
        if (btnIncidents) btnIncidents.className = 'res-tab-btn active';
        if (btnReview) btnReview.className = 'res-tab-btn';
        if (contentIncidents) contentIncidents.style.display = 'block';
        if (contentReview) contentReview.style.display = 'none';
      } else {
        if (btnIncidents) btnIncidents.className = 'res-tab-btn';
        if (btnReview) btnReview.className = 'res-tab-btn active';
        if (contentIncidents) contentIncidents.style.display = 'none';
        if (contentReview) contentReview.style.display = 'block';
      }
    }

    function loadExamIncidents(incidents) {
      activeIncidentsList = incidents || [];
      const countEl = document.getElementById('res-incidents-count');
      if (countEl) countEl.innerText = activeIncidentsList.length;

      setProctoringViolationsCount(activeIncidentsList.length);
      renderIncidentsList();

      if (activeIncidentsList.length > 0) {
        switchResultsTab('incidents');
      } else {
        switchResultsTab('review');
      }
    }

    function renderIncidentsList() {
      const emptyCard = document.getElementById('incidents-empty-card');
      const alertBanner = document.getElementById('incidents-alert-banner');
      const container = document.getElementById('incidents-list-container');
      if (!container) return;

      if (!activeIncidentsList || activeIncidentsList.length === 0) {
        if (emptyCard) emptyCard.style.display = 'block';
        if (alertBanner) alertBanner.style.display = 'none';
        container.innerHTML = '';
        return;
      }

      if (emptyCard) emptyCard.style.display = 'none';
      if (alertBanner) alertBanner.style.display = 'flex';

      let html = '';
      activeIncidentsList.forEach((inc, idx) => {
        const incId = inc.incident_id || `inc_${idx+1}`;
        const timeCode = inc.time_code || '00:00';
        const typeRu = inc.type_ru || inc.type || 'Инцидент';
        const dur = inc.duration_sec ? `${inc.duration_sec} сек` : '1.5 сек';
        const sev = (inc.severity || 'HIGH').toUpperCase();
        const sevClass = (sev === 'CRITICAL') ? 'critical' : 'high';
        const desc = inc.description || '';
        const shotSrc = inc.screenshot_b64 || inc.screenshot || '';

        let appealAreaHtml = '';
        if (!inc.appeal || !inc.appeal.status || inc.appeal.status === 'none') {
          appealAreaHtml = `
            <div class="appeal-action-area">
              <div style="color: #94a3b8; font-size: 12.5px;">Считаете фиксацию ошибочной? Вы можете оспорить данный инцидент:</div>
              <button type="button" class="btn-appeal" onclick="openAppealModal('${incId}')">
                ⚖️ Оспорить / Подать апелляцию
              </button>
            </div>
          `;
        } else if (inc.appeal.status === 'pending') {
          appealAreaHtml = `
            <div class="appeal-action-area">
              <div class="appeal-box pending">
                <span class="appeal-badge pending">На рассмотрении ⏳</span>
                <div class="appeal-meta">
                  <div><strong>Причина:</strong> ${escapeHtml(inc.appeal.reason)}</div>
                  ${inc.appeal.comment ? `<div><strong>Пояснение:</strong> ${escapeHtml(inc.appeal.comment)}</div>` : ''}
                  <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">Подана в ${inc.appeal.submitted_at || ''} • Ожидает решения преподавателя</div>
                </div>
              </div>
            </div>
          `;
        } else if (inc.appeal.status === 'approved') {
          appealAreaHtml = `
            <div class="appeal-action-area">
              <div class="appeal-box approved">
                <span class="appeal-badge approved">✅ Апелляция удовлетворена</span>
                <div class="appeal-meta">
                  <div><strong>Причина:</strong> ${escapeHtml(inc.appeal.reason)}</div>
                  <div style="color: #86efac; margin-top: 4px;"><strong>Вердикт преподавателя:</strong> ${escapeHtml(inc.appeal.teacher_comment || 'Нарушение аннулировано')}</div>
                </div>
              </div>
            </div>
          `;
        } else if (inc.appeal.status === 'rejected') {
          appealAreaHtml = `
            <div class="appeal-action-area">
              <div class="appeal-box rejected">
                <span class="appeal-badge rejected">❌ Апелляция отклонена</span>
                <div class="appeal-meta">
                  <div><strong>Причина:</strong> ${escapeHtml(inc.appeal.reason)}</div>
                  <div style="color: #fca5a5; margin-top: 4px;"><strong>Комментарий преподавателя:</strong> ${escapeHtml(inc.appeal.teacher_comment || 'Апелляция не принята')}</div>
                </div>
              </div>
            </div>
          `;
        }

        const thumbHtml = shotSrc
          ? `<img src="${shotSrc}" class="incident-thumb" alt="Доказательство" onclick="openAppealModal('${incId}')" title="Кликните для просмотра крупно" />`
          : `<div class="incident-thumb" style="display:flex;align-items:center;justify-content:center;color:#64748b;font-size:11px;">Нет фото</div>`;

        html += `
          <div class="incident-appeal-card">
            <div class="incident-card-top">
              <div class="inc-type-tag">
                <span>⚠️</span>
                <span>${idx + 1}. ${escapeHtml(typeRu)}</span>
              </div>
              <span class="inc-sev-tag ${sevClass}">${sev}</span>
            </div>
            <div class="incident-card-body">
              ${thumbHtml}
              <div class="incident-info-col">
                <div class="incident-desc">${escapeHtml(desc)}</div>
                <div class="incident-meta-pills">
                  <span class="meta-sub-pill">⏱️ Таймкод: ${timeCode}</span>
                  <span class="meta-sub-pill">⏳ Длительность: ${dur}</span>
                  <span class="meta-sub-pill">🆔 ${incId}</span>
                </div>
              </div>
            </div>
            ${appealAreaHtml}
          </div>
        `;
      });

      container.innerHTML = html;
    }

    function openAppealModal(incId) {
      const inc = activeIncidentsList.find(item => (item.incident_id === incId || String(item.id) === String(incId)));
      if (!inc) return;

      currentAppealingIncidentId = inc.incident_id || incId;
      const subtitleEl = document.getElementById('appeal-modal-subtitle');
      if (subtitleEl) {
        subtitleEl.innerText = `${inc.type_ru || inc.type} • ⏱️ ${inc.time_code || '00:00'} (Длительность: ${inc.duration_sec || 1.5}с)`;
      }

      const imgEl = document.getElementById('appeal-modal-img');
      const shot = inc.screenshot_b64 || inc.screenshot || '';
      if (imgEl) {
        if (shot) {
          imgEl.src = shot;
          imgEl.style.display = 'inline-block';
        } else {
          imgEl.style.display = 'none';
        }
      }

      const commentInput = document.getElementById('appeal-comment-input');
      if (commentInput) {
        if (inc.appeal && inc.appeal.comment) {
          commentInput.value = inc.appeal.comment;
        } else {
          commentInput.value = '';
        }
      }

      const reasonSelect = document.getElementById('appeal-reason-select');
      if (reasonSelect) {
        if (inc.appeal && inc.appeal.reason) {
          reasonSelect.value = inc.appeal.reason;
        } else {
          reasonSelect.selectedIndex = 0;
        }
      }

      const submitBtn = document.getElementById('btn-submit-appeal');
      if (submitBtn) {
        if (inc.appeal && inc.appeal.status === 'pending') {
          submitBtn.innerText = 'Обновить апелляцию 📤';
        } else {
          submitBtn.innerText = 'Отправить апелляцию 📤';
        }
      }

      const modal = document.getElementById('appeal-modal');
      if (modal) modal.style.display = 'flex';
    }

    function closeAppealModal() {
      const modal = document.getElementById('appeal-modal');
      if (modal) modal.style.display = 'none';
      currentAppealingIncidentId = null;
    }

    function submitAppeal() {
      if (!currentAppealingIncidentId) return;

      const reasonEl = document.getElementById('appeal-reason-select');
      const commentEl = document.getElementById('appeal-comment-input');
      const reason = reasonEl ? reasonEl.value : 'Другая причина';
      const comment = commentEl ? commentEl.value.trim() : '';

      if (!comment) {
        alert('Пожалуйста, укажите пояснение ситуации перед отправкой апелляции.');
        if (commentEl) commentEl.focus();
        return;
      }

      // Optimistic update
      const nowStr = new Date().toLocaleTimeString('ru-RU');
      const appealData = {
        status: 'pending',
        reason: reason,
        comment: comment,
        submitted_at: nowStr,
        teacher_comment: ''
      };

      activeIncidentsList.forEach(inc => {
        if (inc.incident_id === currentAppealingIncidentId || String(inc.id) === String(currentAppealingIncidentId)) {
          inc.appeal = appealData;
        }
      });

      renderIncidentsList();
      closeAppealModal();

      // Dispatch to Python backend via proctor:// scheme
      try {
        const url = `proctor://appeal?id=${encodeURIComponent(currentAppealingIncidentId)}&reason=${encodeURIComponent(reason)}&comment=${encodeURIComponent(comment)}`;
        window.location.href = url;
      } catch (e) {}
    }

    function updateIncidentAppealStatus(incidentId, appealData) {
      if (!activeIncidentsList) return;
      activeIncidentsList.forEach(inc => {
        if (inc.incident_id === incidentId || String(inc.id) === String(incidentId)) {
          inc.appeal = appealData;
        }
      });
      renderIncidentsList();
    }

    // Keyboard navigation prevention (no copy/paste, only arrows)
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && ['c', 'v', 'x', 'a', 's', 'p'].includes(e.key.toLowerCase())) {
        e.preventDefault();
      }
    });

    // Enter key listener on student name input & autofocus
    window.addEventListener('DOMContentLoaded', () => {
      const input = document.getElementById('student-name-input');
      if (input) {
        input.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') {
            submitLoginAndStart();
          }
        });
        setTimeout(() => input.focus(), 200);
      }
    });
  </script>

  <!-- IN-PAGE CONFIRMATION MODAL (NO BROWSER POPUPS) -->
  <div id="confirm-modal" class="modal-backdrop" style="display: none;">
    <div class="modal-card">
      <div class="modal-icon" id="modal-icon">🏁</div>
      <h2 class="modal-title" id="modal-title">Завершить тест?</h2>
      <p class="modal-desc" id="modal-desc">Вы ответили на все 10 вопросов.</p>
      <div class="modal-actions">
        <button type="button" class="btn-modal-cancel" onclick="closeConfirmModal()">Вернуться к вопросам</button>
        <button type="button" class="btn-modal-confirm" id="btn-modal-confirm" onclick="executeFinishExam()">Завершить тест</button>
      </div>
    </div>
  </div>

  <!-- IN-PAGE APPEAL MODAL -->
  <div id="appeal-modal" class="modal-backdrop" style="display: none;">
    <div class="modal-card appeal-modal-card">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
        <div>
          <h2 class="modal-title" style="text-align: left; font-size: 18px; margin-bottom: 4px;">⚖️ Подача апелляции на нарушение</h2>
          <p class="modal-desc" style="text-align: left; margin-bottom: 0;" id="appeal-modal-subtitle">Инцидент #1 • ⏱️ 02:15</p>
        </div>
        <button type="button" class="btn-close-modal" onclick="closeAppealModal()">✕</button>
      </div>

      <!-- Large screenshot preview -->
      <div class="appeal-image-container">
        <img id="appeal-modal-img" src="" alt="Скриншот нарушения" />
      </div>

      <div class="appeal-form-group">
        <label class="appeal-label" for="appeal-reason-select">Типовая причина апелляции:</label>
        <select id="appeal-reason-select" class="appeal-select">
          <option value="Посмотрел на клавиатуру / в черновик">Посмотрел на клавиатуру / в черновик</option>
          <option value="Ложное срабатывание (в руке был предмет, а не телефон)">Ложное срабатывание (в руке был предмет, а не телефон)</option>
          <option value="Посторонний шум / помеха в комнате">Посторонний шум / помеха в комнате</option>
          <option value="Технический сбой камеры / освещения">Технический сбой камеры / освещения</option>
          <option value="Другая причина">Другая причина</option>
        </select>
      </div>

      <div class="appeal-form-group">
        <label class="appeal-label" for="appeal-comment-input">Подробное пояснение ситуации:</label>
        <textarea id="appeal-comment-input" class="appeal-textarea" placeholder="Опишите подробности инцидента, чтобы преподаватель мог учесть контекст (например, что именно вы делали в этот момент)..." rows="4"></textarea>
      </div>

      <div class="modal-actions" style="margin-top: 18px;">
        <button type="button" class="btn-modal-cancel" onclick="closeAppealModal()">Отмена</button>
        <button type="button" class="btn-modal-confirm primary" id="btn-submit-appeal" onclick="submitAppeal()">Отправить апелляцию 📤</button>
      </div>
    </div>
  </div>
</body>
</html>
"""
