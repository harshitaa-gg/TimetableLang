export interface CompileError {
  category: string;
  message: string;
  line?: number | null;
  column?: number | null;
}

export interface TokenItem {
  type: string;
  value: string | null;
  line: number;
  column: number;
}

export interface QuadrupleItem {
  index: number;
  op: string;
  arg1: string;
  arg2: string;
  result: string;
}

export interface AssignmentItem {
  course: string;
  room: string;
  invigilator: string;
  students: string;
  student_group?: string;
  slot: number;
  auto_assigned?: boolean;
}

export interface CompileStages {
  lexer: {
    status: 'pending' | 'running' | 'passed' | 'failed';
    token_count?: number;
    tokens?: TokenItem[];
    error?: string;
  };
  parser: {
    status: 'pending' | 'running' | 'passed' | 'failed';
    declaration_count?: number;
    error?: string;
  };
  ast: {
    status: 'pending' | 'running' | 'passed' | 'failed';
    tree?: string;
    error?: string;
  };
  semantic: {
    status: 'pending' | 'running' | 'passed' | 'failed';
    symbol_tables?: string;
    error?: string;
  };
  ir: {
    status: 'pending' | 'running' | 'passed' | 'failed';
    tac?: string[];
    quadruples?: QuadrupleItem[];
  };
  generator: {
    status: 'pending' | 'running' | 'passed' | 'failed';
    assignments_count?: number;
    slots_used?: number;
    error?: string;
  };
  verifier: {
    status: 'pending' | 'running' | 'passed' | 'failed';
    violations?: string[];
  };
  timetable?: {
    formatted: string;
    by_slot: string;
    assignments: AssignmentItem[];
    slots_used: number[];
  } | null;
}

export interface CompileResponse {
  success: boolean;
  stage_failed?: string | null;
  error?: CompileError | null;
  stages: CompileStages;
}
