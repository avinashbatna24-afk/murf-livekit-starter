import { NextResponse } from 'next/server';
import { execFile } from 'child_process';
import fs from 'fs';
import path from 'path';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);

function getPythonExecutable(): string {
  // 1. Try backend virtualenv python
  const venvPy = path.resolve(process.cwd(), '../backend/.venv/Scripts/python.exe');
  if (fs.existsSync(venvPy)) {
    return venvPy;
  }
  const venvPyLinux = path.resolve(process.cwd(), '../backend/.venv/bin/python');
  if (fs.existsSync(venvPyLinux)) {
    return venvPyLinux;
  }
  // 2. Fallback to system python
  return 'python';
}

export async function GET() {
  try {
    const pythonExe = getPythonExecutable();
    const scriptPath = path.resolve(process.cwd(), '../backend/src/read_analytics.py');
    const dbPath = path.resolve(process.cwd(), '../backend/data/memory.db');

    const { stdout } = await execFileAsync(pythonExe, [scriptPath, dbPath]);
    const data = JSON.parse(
      stdout.trim() ||
        '{"total_calls": 0, "successful_calls": 0, "failed_calls": 0, "success_rate": 0, "recent_calls": []}'
    );
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching analytics API:', error);
    return NextResponse.json(
      {
        total_calls: 0,
        successful_calls: 0,
        failed_calls: 0,
        success_rate: 0,
        avg_duration_seconds: 0,
        failure_breakdown: {},
        channel_breakdown: {},
        recent_calls: [],
      },
      { status: 200 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { outcome, topic, caller_name, reason } = body;

    const pythonExe = getPythonExecutable();
    const dbPath = path.resolve(process.cwd(), '../backend/data/memory.db');

    // Run a python inline snippet to record a test call log
    const callId = `test_call_${Date.now()}`;
    const testTopic = topic || 'Photosynthesis';
    const testName = caller_name || 'Ramesh';
    const testOutcome = outcome || 'successful';
    const testReason =
      reason || (testOutcome === 'failed' ? 'User declined practice exercise' : '');
    const isEx = testOutcome === 'successful' ? 1 : 0;
    const isMem = testOutcome === 'successful' ? 1 : 0;

    const code = `
import sys
from pathlib import Path
src_dir = Path(r"${path.resolve(process.cwd(), '../backend/src')}")
sys.path.insert(0, str(src_dir))
from db import record_call_start, update_call_progress, record_call_end

db_path = Path(r"${dbPath}")
record_call_start("${callId}", "${testName.toLowerCase()}", "${testName}", "Browser", "${testTopic}", db_path=db_path)
update_call_progress("${callId}", exercises_inc=${isEx}, memory_saved=${isMem ? 'True' : 'False'}, topic_discussed="${testTopic}", db_path=db_path)
record_call_end("${callId}", outcome="${testOutcome}", failure_reason="${testReason}", db_path=db_path)
print("OK")
`;

    await execFileAsync(pythonExe, ['-c', code]);

    return NextResponse.json({ success: true, call_id: callId });
  } catch (error) {
    console.error('Error recording test call:', error);
    return NextResponse.json({ success: false, error: 'Internal Server Error' }, { status: 500 });
  }
}
