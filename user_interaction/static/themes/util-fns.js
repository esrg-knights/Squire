/** A better replace text function
 *
 * @param {Node} element
 * @param {RegExp|string} pattern
 * @param {string} replacement
 *
 * @copyright https://stackoverflow.com/a/50537862/4633439
 */
function replaceInText(element, pattern, replacement) {
    for (let node of Array.from(element.childNodes)) { //Array.from because of complicated browser issues
        if (node.isContentEditable) {
            console.debug("node is contentEditable, skipping");
            console.debug(node);
            continue;
        }
        switch (node.nodeType) {
            case Node.ELEMENT_NODE:
                replaceInText(node, pattern, replacement);
                break;
            case Node.TEXT_NODE:
                node.textContent = node.textContent.replace(pattern, replacement);
                break;
            case Node.DOCUMENT_NODE:
                replaceInText(node, pattern, replacement);
                break;
            case Node.COMMENT_NODE:
                break;
            default:
                console.log(`node type not handled (${node.nodeType})`)
        }
    }
}
