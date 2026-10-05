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
  </style>
</head>
<body oncontextmenu="return false;">
  <header>
    <div class="brand">
      <div class="brand-logo">🛡️</div>
      <div class="brand-title">
        <h1>Local proctoring</h1>
        <p>Тестирование: Компьютерное зрение & Системы ИИ (10 вопросов)</p>
      </div>
    </div>
    <div class="exam-meta">
      <div class="timer-pill" id="timer">⏱️ 15:00</div>
    </div>
  </header>

  <main>
    <!-- ACTIVE EXAM CONTAINER -->
    <div id="exam-view">
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
          <button class="btn btn-prev" id="btn-prev" onclick="prevQuestion()">← Назад</button>
        </div>
        <div class="nav-right">
          <button class="btn btn-next" id="btn-next" onclick="nextQuestion()">Далее →</button>
        </div>
      </div>
    </div>

    <!-- EXAM RESULTS CONTAINER -->
    <div id="results-view">
      <div class="results-hero">
        <div class="hero-score-badge" id="res-score-text">0 / 10</div>
        <div class="hero-status-tag" id="res-status-tag">ТЕСТ СДАН</div>

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
            🚪 Выйти из тестирования (Закрыть)
          </button>
          <button class="btn btn-prev" onclick="restartExam()" style="padding: 14px 24px; font-size: 15px;">
            🔄 Пройти заново
          </button>
        </div>
      </div>

      <div class="review-title">
        <span>📋 Подробный разбор каждого вопроса:</span>
      </div>

      <div id="review-cards-list"></div>

      <div style="text-align: center; margin: 30px 0;">
        <button class="btn-exit-app" onclick="exitExam()">
          🚪 Выйти из тестирования (Закрыть)
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

    function renderQuestion() {
      const q = questions[currentIndex];
      document.getElementById('q-curr').innerText = currentIndex + 1;
      document.getElementById('q-total').innerText = questions.length;
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
        btnNext.innerHTML = 'Далее →';
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
      document.getElementById('exam-view').style.display = 'none';
      document.getElementById('results-view').style.display = 'block';
      window.scrollTo({ top: 0, behavior: 'smooth' });

      // Signal Python proctoring system that exam is finished so all alerts/locks/popups are silenced
      try {
        window.location.href = "proctor://finished";
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
      closeConfirmModal();
      timeRemaining = TOTAL_TIME_SECONDS;
      selectedAnswers = {};
      currentIndex = 0;
      document.getElementById('results-view').style.display = 'none';
      document.getElementById('exam-view').style.display = 'block';
      startTimer();
      renderQuestion();
      window.scrollTo({ top: 0, behavior: 'smooth' });

      try {
        window.location.href = "proctor://restarted";
      } catch (e) {}
    }

    // Keyboard navigation prevention (no copy/paste, only arrows)
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && ['c', 'v', 'x', 'a', 's', 'p'].includes(e.key.toLowerCase())) {
        e.preventDefault();
      }
    });

    // Start exam
    renderQuestion();
    startTimer();
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
</body>
</html>
"""
