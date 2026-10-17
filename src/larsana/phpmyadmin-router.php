<?php
// Only the front controller and public static assets are exposed by this server.
$path = rawurldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/');
if (preg_match('~^/(?:vendor|libraries|templates|setup|sql|tmp|sessions)(?:/|$)|(?:^|/)\.|\\\\|\x00~', $path)
    || str_contains($path, '..')) {
    http_response_code(404);
    exit;
}
if (in_array($path, ['/', '/index.php', '/js/messages.php', '/url.php'], true)) {
    define('ROOT_PATH', $_SERVER['DOCUMENT_ROOT'] . '/');
    $file = $path === '/' ? '/index.php' : $path;
    if ($file === '/js/messages.php') {
        chdir($_SERVER['DOCUMENT_ROOT'] . '/js');
    }
    require $_SERVER['DOCUMENT_ROOT'] . $file;
    return true;
}
if (preg_match('~^/(?:themes|js)/.+\.(?:css|js|map|png|jpg|jpeg|gif|svg|ico|woff2?|ttf|eot)$~i', $path)
    || $path === '/favicon.ico' || $path === '/robots.txt') {
    return false;
}
http_response_code(404);
