"""Simplified stand-in for the pytest-cov plugin used in tests."""

from __future__ import annotations

import sys
import threading
import trace
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pytest


@dataclass
class _FileCoverage:
    filename: Path
    executed: Set[int]
    measured: Set[int]

    @property
    def percent(self) -> float:
        if not self.measured:
            return 100.0
        return 100.0 * len(self.executed & self.measured) / len(self.measured)

    @property
    def missing(self) -> List[int]:
        return sorted(self.measured - self.executed)
def _iter_measured_lines(source: str, filename: str) -> Set[int]:
    """Return the set of line numbers that should count towards coverage."""

    try:
        code = compile(source, filename, "exec")
    except SyntaxError:
        return set()

    measured: Set[int] = set()

    def visit(code_obj) -> None:
        measured.add(int(code_obj.co_firstlineno))
        for _start, _end, lineno in code_obj.co_lines():
            if lineno is not None:
                measured.add(int(lineno))
        for const in code_obj.co_consts:
            if isinstance(const, type(code_obj)):
                visit(const)

    visit(code)

    lines = source.splitlines()
    for idx, line in enumerate(lines, start=1):
        if "pragma: no cover" in line:
            measured.discard(idx)
    return {line for line in measured if line > 0}


class _CoverageController:
    def __init__(self, config: pytest.Config, options: Optional[Namespace] = None) -> None:
        self.config = config
        self.targets = [Path(p) for p in self._resolve_option("cov", options, default=[])]
        self.reports = list(self._resolve_option("cov_report", options, default=[]))
        fail_under = self._resolve_option("cov_fail_under", options, default=None)
        self.fail_under = float(fail_under) if fail_under is not None else None
        self.enabled = bool(self.targets)
        self.tracer: Optional[trace.Trace] = None
        self.results: Optional[trace.Results] = None
        self.file_stats: List[_FileCoverage] = []

    def _resolve_option(self, name: str, options: Optional[Namespace], default):
        if options is not None and hasattr(options, name):
            value = getattr(options, name)
            if value is not None:
                return value
        try:
            return self.config.getoption(name)
        except (ValueError, AttributeError):
            return default

    def start(self) -> None:
        if not self.enabled:
            return
        self.tracer = trace.Trace(count=True, trace=False, ignoremods=set(sys.builtin_module_names))
        sys.settrace(self.tracer.globaltrace)
        threading.settrace(self.tracer.globaltrace)

    def stop(self) -> None:
        if not self.enabled or self.tracer is None:
            return
        sys.settrace(None)
        threading.settrace(None)
        self.results = self.tracer.results()

    def _should_measure(self, filename: str) -> bool:
        path = Path(filename).resolve()
        for target in self.targets:
            target_path = target.resolve()
            if path.is_relative_to(target_path):
                return True
        return False

    def _collect_file_stats(self) -> None:
        if self.results is None:
            return
        counts: Dict[str, Dict[int, int]] = {}
        for (filename, lineno), count in self.results.counts.items():
            counts.setdefault(filename, {})[lineno] = count
        for filename, line_counts in counts.items():
            if not self._should_measure(filename):
                continue
            file_path = Path(filename)
            try:
                source_text = file_path.read_text()
            except OSError:
                continue
            measured = _iter_measured_lines(source_text, str(file_path))
            executed = {lineno for lineno, hits in line_counts.items() if hits > 0}
            # Ensure we never report executed lines that were not marked as measured.
            executed.update(lineno for lineno in measured if lineno in line_counts)
            self.file_stats.append(_FileCoverage(file_path, executed, measured))

    def _render_report(self) -> None:
        if "term-missing" not in self.reports:
            return
        terminal = self.config.pluginmanager.get_plugin("terminalreporter")
        if terminal is None:
            return
        terminal.write_line("Coverage report: term-missing", yellow=True)
        for stat in sorted(self.file_stats, key=lambda s: str(s.filename)):
            missing = ",".join(str(num) for num in stat.missing) if stat.missing else ""
            terminal.write_line(f"{stat.filename}: {stat.percent:.1f}% {missing}")

    def _overall_percent(self) -> float:
        measured = sum(len(stat.measured) for stat in self.file_stats)
        executed = sum(len(stat.executed & stat.measured) for stat in self.file_stats)
        if measured == 0:
            return 100.0
        return 100.0 * executed / measured

    def finish(self) -> None:
        if not self.enabled:
            return
        self._collect_file_stats()
        self._render_report()
        overall = self._overall_percent()
        if self.fail_under is not None and overall < float(self.fail_under):
            raise pytest.UsageError(
                f"FAIL Required test coverage of {self.fail_under}% not reached. Total coverage: {overall:.2f}%"
            )
        terminal = self.config.pluginmanager.get_plugin("terminalreporter")
        if terminal is not None:
            terminal.write_line(f"TOTAL COVERAGE: {overall:.2f}%")


_controller: Optional[_CoverageController] = None


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("coverage")
    group.addoption("--cov", action="append", default=[], help="Measure coverage for the given paths")
    group.addoption("--cov-report", dest="cov_report", action="append", default=[], help="Report type")
    group.addoption("--cov-fail-under", dest="cov_fail_under", type=float, help="Fail if coverage is below this value")


def pytest_load_initial_conftests(early_config: pytest.Config, parser: pytest.Parser, args: List[str]) -> None:
    """Start coverage tracing before ``conftest`` modules are imported."""

    global _controller
    options = getattr(early_config, "known_args_namespace", None)
    _controller = _CoverageController(early_config, options=options)
    if _controller.enabled and _controller.tracer is None:
        _controller.start()


def pytest_configure(config: pytest.Config) -> None:
    global _controller
    if _controller is None:
        _controller = _CoverageController(config)
        if _controller.enabled:
            _controller.start()
    else:
        _controller.config = config
    if _controller.enabled:
        config.pluginmanager.register(_controller, "_simple_cov")


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if _controller is None:
        return
    _controller.stop()
    _controller.finish()
