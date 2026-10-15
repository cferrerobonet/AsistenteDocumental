import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import requests

from src.excel_processor import ExcelProcessor
from src.file_downloader import FileDownloader
from src.folder_manager import FolderManager


class FakeAuthManager:
    def __init__(self):
        self.cookies = None


class FakeGraphAuthManager(FakeAuthManager):
    def __init__(self, failures_before_success=0, download_url="https://example.com/file.pdf"):
        super().__init__()
        self.failures_before_success = failures_before_success
        self.calls = 0
        self.download_url = download_url

    def make_graph_request(self, path):
        self.calls += 1
        if self.calls <= self.failures_before_success:
            raise RuntimeError("graph temporal")
        return {"@microsoft.graph.downloadUrl": self.download_url}


class FakeResponse:
    def __init__(self, payload=b"contenido", content_type="application/pdf", url="https://example.com/file.pdf"):
        self._payload = payload
        self.headers = {
            "content-type": content_type,
            "content-length": str(len(payload)),
        }
        self.url = url
        self.content = payload

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size=8192):
        yield self._payload


class FakeHeadResponse:
    def __init__(self, status_code=200, headers=None, url="https://example.com/a.pdf"):
        self.status_code = status_code
        self.headers = headers or {
            "content-type": "application/pdf",
            "content-length": "10",
            "content-disposition": "attachment; filename=archivo.pdf",
        }
        self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


class AuditoriaQualityGateTests(unittest.TestCase):
    def test_excel_processor_detecta_ciclo_y_nombre_archivo_por_campo(self):
        processor = ExcelProcessor()

        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "datos.csv")
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write(
                    "Primer Apellido,Segundo Apellido,Nombre del alumno/a,Indique el ciclo al que pertenece,Documento Identidad\n"
                    "Garcia,Lopez,Ana,SMR,https://example.com/doc.pdf\n"
                )

            loaded = processor.load_excel(csv_path)
            self.assertTrue(loaded)

            detected = processor.detect_columns()
            self.assertTrue(detected["especialidad"])
            self.assertTrue(detected["urls"])

            data = processor.get_processed_data()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["especialidad"], "SMR")
            self.assertEqual(data[0]["etapa"], "SMR")
            self.assertEqual(data[0]["urls"][0]["filename"], "Documento Identidad.pdf")

    def test_folder_manager_usa_especialidad_como_clasificacion(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = FolderManager(tmp_dir)
            student = {
                "primer_apellido": "GARCIA",
                "segundo_apellido": "LOPEZ",
                "nombre": "ANA",
                "especialidad": "SMR",
                "etapa": "SECUNDARIA",
            }

            folder = manager.get_student_folder_path(student)
            self.assertIn("SMR", folder)
            self.assertNotIn("SECUNDARIA", folder)
            self.assertTrue(folder.endswith(os.path.join("SMR", "GARCIA LOPEZ ANA")))

    def test_file_downloader_reintenta_en_error_de_red(self):
        downloader = FileDownloader(FakeAuthManager())

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = os.path.join(tmp_dir, "out.pdf")

            fake_ok = FakeResponse(payload=b"abcdef", content_type="application/pdf")
            with patch.object(
                downloader.download_session,
                "request",
                side_effect=[requests.ConnectionError("fallo temporal"), fake_ok],
            ):
                with patch("src.file_downloader.time.sleep", return_value=None):
                    ok = downloader._download_file_stream("https://example.com/file.pdf", out_path)

            self.assertTrue(ok)
            self.assertTrue(os.path.exists(out_path))
            self.assertGreater(os.path.getsize(out_path), 0)

    def test_excel_processor_soporta_csv_con_punto_y_coma(self):
        processor = ExcelProcessor()

        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "datos_sc.csv")
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write(
                    "Primer Apellido;Nombre del alumno/a;Indique el ciclo al que pertenece;URL\n"
                    "Perez;Luis;DAM;https://example.com/a.pdf\n"
                )

            self.assertTrue(processor.load_excel(csv_path))
            processor.detect_columns()
            data = processor.get_processed_data()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["especialidad"], "DAM")

    def test_excel_processor_validate_data_alerta_si_falta_ciclo_y_url(self):
        processor = ExcelProcessor()

        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "datos_sin_campos.csv")
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write("Primer Apellido,Nombre\nGarcia,Ana\n")

            self.assertTrue(processor.load_excel(csv_path))
            processor.detect_columns()
            warnings = processor.validate_data()
            joined = " | ".join(warnings)
            self.assertIn("No se detectaron columnas con URLs", joined)
            self.assertIn("No se detectó la columna de ciclo/especialidad", joined)

    def test_folder_manager_normaliza_nombre_sin_invalidos(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = FolderManager(tmp_dir)
            normalized = manager._normalize_folder_name("D.A.M/1* ?_mañana")
            self.assertNotIn("/", normalized)
            self.assertNotIn("*", normalized)
            self.assertNotIn("_", normalized)

    def test_file_downloader_validate_url_invalida(self):
        downloader = FileDownloader(FakeAuthManager())
        result = downloader.validate_url("no-es-url")
        self.assertFalse(result["valid"])
        self.assertIn("inválido", result["error"])

    def test_file_downloader_sanitize_filename(self):
        downloader = FileDownloader(FakeAuthManager())
        clean = downloader._sanitize_filename('te:st/archivo?.pdf')
        self.assertEqual(clean, 'te_st_archivo_.pdf')

    def test_file_downloader_reintento_graph_url_directa(self):
        auth = FakeGraphAuthManager(failures_before_success=2, download_url="https://files.test/doc.pdf")
        downloader = FileDownloader(auth)

        with patch("src.file_downloader.time.sleep", return_value=None):
            direct_url = downloader._get_direct_download_url("https://tenant.sharepoint.com/shared")

        self.assertEqual(direct_url, "https://files.test/doc.pdf")
        self.assertEqual(auth.calls, 3)

    def test_file_downloader_detecta_html_pequeno_como_corrupto(self):
        downloader = FileDownloader(FakeAuthManager())
        html_response = FakeResponse(payload=b"<html>err</html>", content_type="text/html")

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = os.path.join(tmp_dir, "out.html")
            with patch.object(downloader, "_request_with_retries", return_value=html_response):
                ok = downloader._download_file_stream("https://example.com/file", out_path)

        self.assertFalse(ok)

    def test_file_downloader_download_file_falla_url_invalida(self):
        downloader = FileDownloader(FakeAuthManager())
        result = downloader.download_file("", destination_path=tempfile.gettempdir())
        self.assertFalse(result["success"])
        self.assertIsNotNone(result["error"])


if __name__ == "__main__":
    unittest.main()
