---
name: soap-wcf-integrations
description: >-
  Use this skill when developing, refactoring, or testing SOAP 1.1 WCF operations, defusedxml parsing, or httpx integrations with the SEGIP external service in ms-segip.
---

# SOAP 1.1 & WCF Integration — ms-segip Runbook

Este manual describe el flujo de comunicación, construcción de sobres XML y manejo de respuestas para los servicios SOAP 1.1 (WCF `.svc`) de SEGIP.

---

## 1. Estructura Canónica de Sobres SOAP 1.1

El servicio WCF de SEGIP (`ServicioConsultaDatoPersonasExterna.svc`) espera sobres SOAP 1.1 bajo el namespace XML `http://tempuri.org/`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <{OPERACION} xmlns="http://tempuri.org/">
      <pCodigoInstitucion>{CODIGO}</pCodigoInstitucion>
      <pUsuario>{USUARIO}</pUsuario>
      <pContrasenia>{CONTRASENIA}</pContrasenia>
      <pClaveAccesoUsuarioFinal>{CLAVE_FINAL}</pClaveAccesoUsuarioFinal>
      <!-- Parámetros específicos de la operación -->
    </{OPERACION}>
  </soap:Body>
</soap:Envelope>
```

### Cabeceras HTTP Requeridas:
* `Content-Type`: `text/xml; charset=utf-8`
* `SOAPAction`: `"http://tempuri.org/IServicioConsultaDatoPersonasExterna/{OPERACION}"`

---

## 2. Prevención de Vulnerabilidades XML con `defusedxml`

**Nunca** utilizar `xml.etree.ElementTree` o `xml.dom.minidom` estándar sin protección, para prevenir ataques de inyección de entidades externas (XXE) y bombas XML:

```python
import defusedxml.minidom

# Parseo seguro
dom = defusedxml.minidom.parseString(xml_content.encode("utf-8"))
```

Para extraer texto de un nodo XML de forma segura:
```python
elements = dom.getElementsByTagName(tag_name)
if elements and elements[0].firstChild:
    return elements[0].firstChild.nodeValue
return None
```

---

## 3. Sobrescritura de Dirección del Endpoint WSDL

> [!IMPORTANT]
> El contrato WSDL oficial de SEGIP publica internamente la dirección `https://wsverificacion.segip.gob.bo/ServicioExternoInstitucion.svc`.
> El cliente SOAP (`app/integrations/segip/client.py`) debe enviar las peticiones HTTP a la dirección institucional configurada en `SEGIP_SERVICE_URL` (`https://segip-api.fiscalia.gob.bo/ServicioExternoInstitucion.svc`), ignorando el host publicado en el WSDL.

---

## 4. Desempaquetado de JSON Embebido

Varias operaciones (como `ConsultaDatoPersonaEnJson` y `ConsultaDocumentoDatoPersonaEnJson`) devuelven el resultado dentro de la etiqueta `<{OPERACION}Result>`, la cual contiene una cadena de texto en formato JSON.

Flujo de desempaquetado:
1. Extraer el valor textual de `<ConsultaDatoPersonaEnJsonResult>`.
2. Decodificar la cadena con `json.loads(resultado_str)`.
3. Validar el campo de control `CodigoRespuesta` (código `1` indica consulta exitosa).
4. Mapear los campos mediante `app/integrations/segip/mapper.py` al esquema de dominio `PersonaNormalizada`.

---

## 5. Manejo de Fallos SOAP y Excepciones de Dominio

El cliente debe interceptar respuestas de error y traducirlas a la jerarquía de excepciones de `app/core/exceptions.py`:

| Escenario SOAP | Excepción Interna | Código HTTP Resultante |
| :--- | :--- | :---: |
| Timeout de conexión o lectura (`httpx.TimeoutException`) | `SegipTimeoutException` | **504 Gateway Timeout** |
| Error de conexión o red caída (`httpx.NetworkError`) | `SegipUnavailableException` | **503 Service Unavailable** |
| Credenciales inválidas o acceso denegado | `SegipAuthException` | **401 Unauthorized** |
| Ciudadano no encontrado en la base de datos | `SegipNoResultsException` | **404 Not Found** |
| SOAP Fault (`<soap:Fault>`) | `SegipSoapFaultError` | **502 Bad Gateway** |

---

## 6. Pruebas de Integración con SEGIP Real

Para ejecutar pruebas contra la intranet institucional:

```bash
# 1. Asegurar conectividad a la VPN / red institucional
# 2. Ejecutar la prueba de integración
RUN_SEGIP_INTEGRATION_TESTS=true pytest tests/integration/test_segip_live.py -v -s
```
