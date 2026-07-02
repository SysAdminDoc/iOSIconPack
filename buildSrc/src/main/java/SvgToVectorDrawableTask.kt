import org.gradle.api.DefaultTask
import org.gradle.api.file.ConfigurableFileCollection
import org.gradle.api.file.DirectoryProperty
import org.gradle.api.tasks.InputFiles
import org.gradle.api.tasks.OutputDirectory
import org.gradle.api.tasks.PathSensitive
import org.gradle.api.tasks.PathSensitivity
import org.gradle.api.tasks.TaskAction
import org.w3c.dom.Element
import org.w3c.dom.Node
import java.io.File
import java.math.BigDecimal
import java.util.Locale
import javax.xml.parsers.DocumentBuilderFactory

abstract class SvgToVectorDrawableTask : DefaultTask() {
    @get:InputFiles
    @get:PathSensitive(PathSensitivity.RELATIVE)
    val sourceFiles: ConfigurableFileCollection = project.objects.fileCollection()

    @get:OutputDirectory
    abstract val outputDir: DirectoryProperty

    @TaskAction
    fun convert() {
        val sources = sourceFiles.files
            .filter { it.isFile && it.extension.equals("svg", ignoreCase = true) }
            .sortedBy { it.invariantSeparatorsPath }
        val output = outputDir.get().asFile
        if (output.exists()) {
            output.deleteRecursively()
        }
        output.mkdirs()

        val resourceNames = mutableSetOf<String>()
        for (source in sources) {
            val resourceName = source.nameWithoutExtension.toDrawableResourceName()
            require(resourceNames.add(resourceName)) {
                "Duplicate generated drawable name '$resourceName' from ${source.invariantSeparatorsPath}"
            }
            val vectorXml = SvgVectorConverter(source).convert()
            File(output, "$resourceName.xml").writeText(vectorXml, Charsets.UTF_8)
        }

        logger.lifecycle(
            "iOSIconPack: converted ${sources.size} SVG source(s) to " +
                output.relativeTo(project.projectDir).invariantSeparatorsPath
        )
    }
}

private data class ViewBox(
    val minX: Double,
    val minY: Double,
    val width: Double,
    val height: Double,
)

private class SvgVectorConverter(private val source: File) {
    fun convert(): String {
        val root = parseRoot(source)
        val viewBox = parseViewBox(root)
        val paths = mutableListOf<String>()
        collectPaths(root, emptyMap(), paths)
        require(paths.isNotEmpty()) {
            "${source.invariantSeparatorsPath}: no supported visible SVG paths found"
        }
        return vectorXml(source.name, viewBox, paths)
    }

    private fun collectPaths(element: Element, inheritedStyle: Map<String, String>, paths: MutableList<String>) {
        if (element.hasAttribute("transform")) {
            unsupported(element, "transform")
        }

        val style = element.mergedStyle(inheritedStyle)
        when (element.localTagName()) {
            "svg", "g", "a", "symbol" -> collectChildPaths(element, style, paths)
            "defs", "title", "desc", "metadata" -> return
            "path" -> addPath(element, style, element.attr("d"), paths)
            "rect" -> addPath(element, style, rectPath(element), paths)
            "circle" -> addPath(element, style, circlePath(element), paths)
            "ellipse" -> addPath(element, style, ellipsePath(element), paths)
            "line" -> addPath(element, style, linePath(element), paths)
            "polygon" -> addPath(element, style, pointsPath(element, close = true), paths)
            "polyline" -> addPath(element, style, pointsPath(element, close = false), paths)
            else -> unsupported(element, "element <${element.tagName}>")
        }
    }

    private fun collectChildPaths(element: Element, style: Map<String, String>, paths: MutableList<String>) {
        val children = element.childNodes
        for (i in 0 until children.length) {
            val child = children.item(i)
            if (child.nodeType == Node.ELEMENT_NODE) {
                collectPaths(child as Element, style, paths)
            }
        }
    }

    private fun addPath(element: Element, style: Map<String, String>, pathData: String, paths: MutableList<String>) {
        if (pathData.isBlank()) return
        val fill = style["fill"] ?: defaultFillFor(element)
        val stroke = style["stroke"] ?: "none"
        if (fill.equals("none", ignoreCase = true) && stroke.equals("none", ignoreCase = true)) {
            return
        }

        val attrs = linkedMapOf<String, String>()
        if (!fill.equals("none", ignoreCase = true)) {
            attrs["android:fillColor"] = fill.toAndroidColor(element, "fill")
            alphaValue(style, "fill-opacity")?.let { attrs["android:fillAlpha"] = it }
            if (style["fill-rule"].equals("evenodd", ignoreCase = true)) {
                attrs["android:fillType"] = "evenOdd"
            }
        } else {
            attrs["android:fillColor"] = "#00000000"
        }

        if (!stroke.equals("none", ignoreCase = true)) {
            attrs["android:strokeColor"] = stroke.toAndroidColor(element, "stroke")
            attrs["android:strokeWidth"] = style["stroke-width"]?.toSvgDouble(element, "stroke-width")?.fmt() ?: "1"
            style["stroke-linecap"]?.let { attrs["android:strokeLineCap"] = it }
            style["stroke-linejoin"]?.let { attrs["android:strokeLineJoin"] = it }
            alphaValue(style, "stroke-opacity")?.let { attrs["android:strokeAlpha"] = it }
        }

        attrs["android:pathData"] = pathData
        paths += "    <path ${attrs.toXmlAttributes()} />"
    }

    private fun defaultFillFor(element: Element): String {
        return when (element.localTagName()) {
            "line", "polyline" -> "none"
            else -> "#000000"
        }
    }

    private fun vectorXml(sourceName: String, viewBox: ViewBox, paths: List<String>): String {
        val body = if (viewBox.minX == 0.0 && viewBox.minY == 0.0) {
            paths.joinToString("\n")
        } else {
            buildString {
                appendLine(
                    "    <group android:translateX=\"${(-viewBox.minX).fmt()}\" " +
                        "android:translateY=\"${(-viewBox.minY).fmt()}\">"
                )
                appendLine(paths.joinToString("\n") { "    $it" })
                append("    </group>")
            }
        }
        return buildString {
            appendLine("<?xml version=\"1.0\" encoding=\"utf-8\"?>")
            appendLine("<!-- Generated from app/src/main/svg/$sourceName by convertSvgSources. -->")
            appendLine("<vector xmlns:android=\"http://schemas.android.com/apk/res/android\"")
            appendLine("    android:width=\"${viewBox.width.fmt()}dp\"")
            appendLine("    android:height=\"${viewBox.height.fmt()}dp\"")
            appendLine("    android:viewportWidth=\"${viewBox.width.fmt()}\"")
            appendLine("    android:viewportHeight=\"${viewBox.height.fmt()}\">")
            appendLine(body)
            appendLine("</vector>")
        }
    }

    private fun parseRoot(source: File): Element {
        val factory = DocumentBuilderFactory.newInstance()
        factory.isNamespaceAware = true
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false)
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false)
        factory.setAttribute("http://javax.xml.XMLConstants/property/accessExternalDTD", "")
        factory.setAttribute("http://javax.xml.XMLConstants/property/accessExternalSchema", "")
        val root = factory.newDocumentBuilder().parse(source).documentElement
        require(root.localTagName() == "svg") {
            "${source.invariantSeparatorsPath}: root element must be <svg>"
        }
        return root
    }

    private fun parseViewBox(root: Element): ViewBox {
        val rawViewBox = root.attr("viewBox")
        if (rawViewBox.isNotBlank()) {
            val values = rawViewBox.split(Regex("[,\\s]+")).filter { it.isNotBlank() }
            require(values.size == 4) {
                "${source.invariantSeparatorsPath}: viewBox must contain four numbers"
            }
            val minX = values[0].toSvgDouble(root, "viewBox")
            val minY = values[1].toSvgDouble(root, "viewBox")
            val width = values[2].toSvgDouble(root, "viewBox")
            val height = values[3].toSvgDouble(root, "viewBox")
            require(width > 0.0 && height > 0.0) {
                "${source.invariantSeparatorsPath}: viewBox width and height must be positive"
            }
            return ViewBox(minX, minY, width, height)
        }

        val width = root.attr("width").toSvgDouble(root, "width")
        val height = root.attr("height").toSvgDouble(root, "height")
        require(width > 0.0 && height > 0.0) {
            "${source.invariantSeparatorsPath}: width and height must be positive"
        }
        return ViewBox(0.0, 0.0, width, height)
    }

    private fun rectPath(element: Element): String {
        val x = element.optionalDouble("x")
        val y = element.optionalDouble("y")
        val width = element.requiredDouble("width")
        val height = element.requiredDouble("height")
        val rx = element.optionalDouble("rx")
        val ry = element.optionalDouble("ry")
        require(width > 0.0 && height > 0.0) {
            "${source.invariantSeparatorsPath}: <rect> width and height must be positive"
        }
        if (rx == 0.0 && ry == 0.0) {
            return "M${x.fmt()},${y.fmt()} H${(x + width).fmt()} V${(y + height).fmt()} " +
                "H${x.fmt()} Z"
        }
        val cornerX = rx.coerceAtMost(width / 2.0)
        val cornerY = (if (ry == 0.0) rx else ry).coerceAtMost(height / 2.0)
        return "M${(x + cornerX).fmt()},${y.fmt()} H${(x + width - cornerX).fmt()} " +
            "A${cornerX.fmt()},${cornerY.fmt()} 0,0,1 ${(x + width).fmt()},${(y + cornerY).fmt()} " +
            "V${(y + height - cornerY).fmt()} " +
            "A${cornerX.fmt()},${cornerY.fmt()} 0,0,1 ${(x + width - cornerX).fmt()},${(y + height).fmt()} " +
            "H${(x + cornerX).fmt()} " +
            "A${cornerX.fmt()},${cornerY.fmt()} 0,0,1 ${x.fmt()},${(y + height - cornerY).fmt()} " +
            "V${(y + cornerY).fmt()} " +
            "A${cornerX.fmt()},${cornerY.fmt()} 0,0,1 ${(x + cornerX).fmt()},${y.fmt()} Z"
    }

    private fun circlePath(element: Element): String {
        val cx = element.requiredDouble("cx")
        val cy = element.requiredDouble("cy")
        val r = element.requiredDouble("r")
        require(r > 0.0) { "${source.invariantSeparatorsPath}: <circle> radius must be positive" }
        return ellipsePath(cx, cy, r, r)
    }

    private fun ellipsePath(element: Element): String {
        val cx = element.requiredDouble("cx")
        val cy = element.requiredDouble("cy")
        val rx = element.requiredDouble("rx")
        val ry = element.requiredDouble("ry")
        require(rx > 0.0 && ry > 0.0) {
            "${source.invariantSeparatorsPath}: <ellipse> radii must be positive"
        }
        return ellipsePath(cx, cy, rx, ry)
    }

    private fun ellipsePath(cx: Double, cy: Double, rx: Double, ry: Double): String {
        return "M${(cx - rx).fmt()},${cy.fmt()} " +
            "A${rx.fmt()},${ry.fmt()} 0,1,0 ${(cx + rx).fmt()},${cy.fmt()} " +
            "A${rx.fmt()},${ry.fmt()} 0,1,0 ${(cx - rx).fmt()},${cy.fmt()} Z"
    }

    private fun linePath(element: Element): String {
        return "M${element.requiredDouble("x1").fmt()},${element.requiredDouble("y1").fmt()} " +
            "L${element.requiredDouble("x2").fmt()},${element.requiredDouble("y2").fmt()}"
    }

    private fun pointsPath(element: Element, close: Boolean): String {
        val values = element.attr("points").split(Regex("[,\\s]+")).filter { it.isNotBlank() }
        require(values.size >= 4 && values.size % 2 == 0) {
            "${source.invariantSeparatorsPath}: <${element.tagName}> points must be x/y pairs"
        }
        val pairs = values.chunked(2).map { (x, y) ->
            x.toSvgDouble(element, "points") to y.toSvgDouble(element, "points")
        }
        val first = pairs.first()
        val rest = pairs.drop(1).joinToString(" ") { (x, y) -> "L${x.fmt()},${y.fmt()}" }
        return "M${first.first.fmt()},${first.second.fmt()} $rest${if (close) " Z" else ""}"
    }

    private fun unsupported(element: Element, feature: String): Nothing {
        throw IllegalArgumentException(
            "${source.invariantSeparatorsPath}: unsupported SVG $feature on <${element.tagName}>"
        )
    }
}

private fun Element.mergedStyle(parent: Map<String, String>): Map<String, String> {
    val merged = parent.toMutableMap()
    val presentationAttrs = listOf(
        "fill",
        "stroke",
        "stroke-width",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-opacity",
        "fill-opacity",
        "fill-rule",
        "opacity",
    )
    for (name in presentationAttrs) {
        attr(name).takeIf { it.isNotBlank() }?.let { merged[name] = it }
    }
    for (entry in attr("style").split(";")) {
        val parts = entry.split(":", limit = 2)
        if (parts.size == 2) {
            merged[parts[0].trim()] = parts[1].trim()
        }
    }
    merged["opacity"]?.let { opacity ->
        if (!merged.containsKey("fill-opacity")) merged["fill-opacity"] = opacity
        if (!merged.containsKey("stroke-opacity")) merged["stroke-opacity"] = opacity
    }
    return merged
}

private fun Element.localTagName(): String {
    return (localName ?: tagName).substringAfter(':').lowercase(Locale.US)
}

private fun Element.attr(name: String): String = getAttribute(name).trim()

private fun Element.optionalDouble(name: String): Double {
    return attr(name).takeIf { it.isNotBlank() }?.toSvgDouble(this, name) ?: 0.0
}

private fun Element.requiredDouble(name: String): Double {
    val raw = attr(name)
    require(raw.isNotBlank()) { "Missing required '$name' on <${tagName}>" }
    return raw.toSvgDouble(this, name)
}

private fun String.toSvgDouble(element: Element, attrName: String): Double {
    val raw = trim()
    require(!raw.endsWith("%")) { "Unsupported percentage value '$raw' for $attrName on <${element.tagName}>" }
    val match = Regex("""^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?""").find(raw)
    require(match != null) { "Invalid numeric value '$raw' for $attrName on <${element.tagName}>" }
    return match.value.toDouble()
}

private fun alphaValue(style: Map<String, String>, name: String): String? {
    val raw = style[name]?.trim()?.takeIf { it.isNotBlank() } ?: return null
    val value = raw.toDoubleOrNull()
    require(value != null && value in 0.0..1.0) { "Invalid $name value '$raw'" }
    return value.fmt()
}

private fun String.toAndroidColor(element: Element, attrName: String): String {
    val raw = trim()
    if (raw.equals("none", ignoreCase = true)) return "#00000000"
    if (raw.startsWith("url(")) {
        throw IllegalArgumentException("Unsupported paint server '$raw' for $attrName on <${element.tagName}>")
    }
    val named = mapOf(
        "black" to "#000000",
        "white" to "#FFFFFF",
        "transparent" to "#00000000",
    )
    named[raw.lowercase(Locale.US)]?.let { return it }
    if (raw.startsWith("#")) {
        val hex = raw.removePrefix("#")
        return when (hex.length) {
            3 -> "#" + hex.map { "$it$it" }.joinToString("").uppercase(Locale.US)
            4 -> {
                val expanded = hex.map { "$it$it" }
                "#${expanded[3]}${expanded[0]}${expanded[1]}${expanded[2]}".uppercase(Locale.US)
            }
            6 -> "#${hex.uppercase(Locale.US)}"
            8 -> "#${hex.substring(6, 8)}${hex.substring(0, 6)}".uppercase(Locale.US)
            else -> throw IllegalArgumentException("Unsupported color '$raw' for $attrName on <${element.tagName}>")
        }
    }
    val rgbMatch = Regex("""rgba?\(([^)]+)\)""", RegexOption.IGNORE_CASE).matchEntire(raw)
    if (rgbMatch != null) {
        val parts = rgbMatch.groupValues[1].split(",").map { it.trim() }
        require(parts.size == 3 || parts.size == 4) {
            "Unsupported color '$raw' for $attrName on <${element.tagName}>"
        }
        val channels = parts.take(3).map { it.toDouble().toInt().coerceIn(0, 255) }
        val alpha = if (parts.size == 4) {
            (parts[3].toDouble().coerceIn(0.0, 1.0) * 255.0).toInt()
        } else {
            null
        }
        return if (alpha == null) {
            "#%02X%02X%02X".format(channels[0], channels[1], channels[2])
        } else {
            "#%02X%02X%02X%02X".format(alpha, channels[0], channels[1], channels[2])
        }
    }
    throw IllegalArgumentException("Unsupported color '$raw' for $attrName on <${element.tagName}>")
}

private fun Map<String, String>.toXmlAttributes(): String {
    return entries.joinToString(" ") { (key, value) -> "$key=\"${value.escapeXmlAttr()}\"" }
}

private fun String.escapeXmlAttr(): String {
    return replace("&", "&amp;")
        .replace("\"", "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
}

private fun Double.fmt(): String {
    val cleaned = BigDecimal.valueOf(this).stripTrailingZeros().toPlainString()
    return if (cleaned == "-0") "0" else cleaned
}

private fun String.toDrawableResourceName(): String {
    val normalized = lowercase(Locale.US)
        .replace(Regex("[^a-z0-9_]+"), "_")
        .replace(Regex("_+"), "_")
        .trim('_')
    return when {
        normalized.isBlank() -> "svg_asset"
        normalized.first().isLetter() || normalized.first() == '_' -> normalized
        else -> "svg_$normalized"
    }
}

private val File.invariantSeparatorsPath: String
    get() = path.replace(File.separatorChar, '/')
