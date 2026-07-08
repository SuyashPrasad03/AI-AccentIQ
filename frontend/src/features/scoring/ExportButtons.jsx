import { useState } from "react";

/**
 * ExportButtons — Download PDF, JSON, Print, Share
 */
export function ExportButtons({ score, recordingId }) {
  const [exporting, setExporting] = useState(false);

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(score, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `pronunciation-report-${recordingId}.json`;
    a.click(); URL.revokeObjectURL(url);
  };

  const exportPDF = async () => {
    setExporting(true);
    try {
      const html2canvas = (await import("html2canvas")).default;
      const { jsPDF } = await import("jspdf");
      const el = document.getElementById("results-container");
      if (!el) return;
      const canvas = await html2canvas(el, { scale: 2, useCORS: true, backgroundColor: "#ffffff" });
      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF("p", "mm", "a4");
      const width = pdf.internal.pageSize.getWidth();
      const height = (canvas.height * width) / canvas.width;
      pdf.addImage(imgData, "PNG", 0, 0, width, height);
      pdf.save(`pronunciation-report-${recordingId}.pdf`);
    } catch (_e) {
      alert("PDF export failed. Try using Print instead.");
    } finally {
      setExporting(false);
    }
  };

  const handlePrint = () => window.print();

  const handleShare = async () => {
    const text = `My pronunciation score: ${Math.round(score.overall_score)}/100 (Accuracy: ${Math.round(score.accuracy_score)}, Fluency: ${Math.round(score.fluency_score)})`;
    if (navigator.share) {
      try { await navigator.share({ title: "Pronunciation Report", text }); } catch (_e) { /* user cancelled */ }
    } else {
      await navigator.clipboard.writeText(text);
      alert("Report summary copied to clipboard!");
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      <button className="btn-secondary !text-xs !px-3 !py-1.5" onClick={exportPDF} disabled={exporting}>
        {exporting ? "Exporting…" : "📄 PDF"}
      </button>
      <button className="btn-secondary !text-xs !px-3 !py-1.5" onClick={exportJSON}>
        📋 JSON
      </button>
      <button className="btn-secondary !text-xs !px-3 !py-1.5" onClick={handlePrint}>
        🖨️ Print
      </button>
      <button className="btn-secondary !text-xs !px-3 !py-1.5" onClick={handleShare}>
        🔗 Share
      </button>
    </div>
  );
}
