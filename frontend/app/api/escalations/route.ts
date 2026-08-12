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
    const scriptPath = path.resolve(process.cwd(), '../backend/src/read_escalations.py');
    const dbPath = path.resolve(process.cwd(), '../backend/data/memory.db');

    const { stdout } = await execFileAsync(pythonExe, [scriptPath, dbPath]);
    const data = JSON.parse(stdout.trim() || '[]');
    return NextResponse.json({ escalations: data });
  } catch (error) {
    console.error('Error fetching escalations API:', error);
    return NextResponse.json({ escalations: [] }, { status: 200 });
  }
}

export async function PATCH(request: Request) {
  try {
    const body = await request.json();
    const { ref_id, status } = body;

    if (!ref_id || !status) {
      return NextResponse.json({ error: 'Missing ref_id or status' }, { status: 400 });
    }

    const pythonExe = getPythonExecutable();
    const scriptPath = path.resolve(process.cwd(), '../backend/src/update_escalation.py');
    const dbPath = path.resolve(process.cwd(), '../backend/data/memory.db');

    const { stdout } = await execFileAsync(pythonExe, [scriptPath, dbPath, ref_id, status]);
    const res = JSON.parse(stdout.trim() || '{"success": false}');
    return NextResponse.json(res);
  } catch (error) {
    console.error('Error updating escalation API:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
